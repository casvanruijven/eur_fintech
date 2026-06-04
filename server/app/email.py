"""Email a receipt (or credit note) to the user / their accountant.

What gets attached: the human-readable **PDF** *and* the machine-readable
**EN 16931 UBL** e-invoice — so the accountant can both read it and import it
straight into bookkeeping software.

In development (no SMTP host configured) the email is logged to the console
instead of being sent, so the whole flow can be demoed offline. A real SMTP path
(aiosmtplib) is kept for when ``ZZPAY_SMTP_*`` is configured.
"""

import logging
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

import aiosmtplib

from app.config import settings
from app.models import CreditNote, Receipt, User
from app.pdf import (
    credit_note_filename,
    receipt_filename,
    render_credit_note_pdf,
    render_pdf,
)
from app.ubl import render_credit_note_ubl, render_ubl

logger = logging.getLogger("zzpay.email")


def _from_header(sender_name: str) -> str:
    # Providers rewrite the From address to the authenticated account, so we name
    # the sender in the display and let Reply-To carry their real address.
    from_address = parseaddr(settings.smtp_from)[1] or settings.smtp_from
    return formataddr((f"{sender_name} via ZZPay", from_address))


async def _deliver(msg: EmailMessage, to: str, summary: str) -> dict:
    """Send the message, or (dev / no SMTP) log it. Returns a mock-able status."""
    if not settings.smtp_host:
        logger.info("EMAIL (dev, not sent) -> %s | %s", to, summary)
        return {"to": to, "delivered": True, "transport": "log"}

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_tls,
    )
    logger.info("Email sent to %s (%s)", to, summary)
    return {"to": to, "delivered": True, "transport": "smtp"}


async def send_receipt_email(to: str, receipt: Receipt, buyer: User) -> dict:
    """Email the receipt as PDF + UBL on behalf of ``buyer`` (the logged-in ZZP'er)."""
    sender_name = f"{buyer.first_name} {buyer.last_name}".strip()
    pdf_bytes = render_pdf(receipt)
    ubl_bytes = render_ubl(receipt, buyer)  # may raise UblComplianceError -> 422 upstream

    msg = EmailMessage()
    msg["From"] = _from_header(sender_name)
    msg["Reply-To"] = formataddr((sender_name, buyer.email))
    msg["To"] = to
    msg["Subject"] = f"Receipt {receipt.invoice_id} — {receipt.supplier_name}"
    msg.set_content(
        f"Hi,\n\n{sender_name} ({buyer.email}) shared a ZZPay receipt with you.\n\n"
        f"Attached: the receipt PDF and a structured e-invoice (UBL, EN 16931) for "
        f"{receipt.supplier_name} dated {receipt.issue_date}, total "
        f"{receipt.currency} {receipt.payable_amount:.2f}.\n\n"
        f"The UBL file imports directly into bookkeeping software.\n\nZZPay"
    )
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                       filename=receipt_filename(receipt, "pdf"))
    msg.add_attachment(ubl_bytes, maintype="application", subtype="xml",
                       filename=receipt_filename(receipt, "xml"))
    return await _deliver(msg, to, f"receipt {receipt.invoice_id} (PDF + UBL)")


async def send_credit_note_email(
    to: str, cn: CreditNote, original: Receipt, buyer: User
) -> dict:
    """Email a credit note as PDF + UBL (mirrors the receipt email)."""
    sender_name = f"{buyer.first_name} {buyer.last_name}".strip()
    pdf_bytes = render_credit_note_pdf(cn, original)
    ubl_bytes = render_credit_note_ubl(cn, buyer, original)

    msg = EmailMessage()
    msg["From"] = _from_header(sender_name)
    msg["Reply-To"] = formataddr((sender_name, buyer.email))
    msg["To"] = to
    msg["Subject"] = f"Credit note {cn.credit_note_id} (corrects {cn.original_receipt_id})"
    msg.set_content(
        f"Hi,\n\nAttached is credit note {cn.credit_note_id}, which corrects receipt "
        f"{cn.original_receipt_id} ({original.supplier_name}). Refund total "
        f"{cn.currency} {cn.payable_amount:.2f}. The original receipt remains valid; "
        f"this linked credit note keeps the administration auditable.\n\n"
        f"PDF and structured UBL e-invoice attached.\n\nZZPay"
    )
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf",
                       filename=credit_note_filename(cn, "pdf"))
    msg.add_attachment(ubl_bytes, maintype="application", subtype="xml",
                       filename=credit_note_filename(cn, "xml"))
    return await _deliver(msg, to, f"credit note {cn.credit_note_id} (PDF + UBL)")

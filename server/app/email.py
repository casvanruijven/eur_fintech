"""Email a receipt PDF to the user or their accountant.

In development (no SMTP host configured) the email is logged to the console
instead of being sent, so the whole flow can be demoed offline.
"""

import logging
from email.message import EmailMessage
from email.utils import formataddr, parseaddr

import aiosmtplib

from app.config import settings
from app.models import Receipt, User
from app.pdf import receipt_filename, render_pdf

logger = logging.getLogger("zzpay.email")


def _build_message(to: str, receipt: Receipt, pdf_bytes: bytes, sender: User) -> EmailMessage:
    sender_name = f"{sender.first_name} {sender.last_name}".strip()
    # Gmail (and most providers) rewrite the From address to the authenticated
    # account, so we can't put the user's address there. Instead we name them in
    # the From display, point Reply-To at them, and say so in the body — that way
    # the recipient (e.g. the accountant) sees exactly who sent the receipt.
    from_address = parseaddr(settings.smtp_from)[1] or settings.smtp_from

    msg = EmailMessage()
    msg["From"] = formataddr((f"{sender_name} via ZZPay", from_address))
    msg["Reply-To"] = formataddr((sender_name, sender.email))
    msg["To"] = to
    msg["Subject"] = f"Kassabon van {sender_name} — {receipt.merchant_name}"
    msg.set_content(
        f"Hoi,\n\n{sender_name} ({sender.email}) heeft een kassabon met je gedeeld via ZZPay.\n\n"
        f"In de bijlage vind je de kassabon van {receipt.merchant_name} "
        f"({receipt.purchased_at:%d-%m-%Y}) ter waarde van "
        f"{receipt.currency} {receipt.total_amount:.2f}.\n\n"
        f"Reageren? Antwoord op deze mail en je bericht gaat naar {sender.email}.\n\n"
        f"Groet,\nZZPay"
    )
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=receipt_filename(receipt, "pdf"),
    )
    return msg


async def send_receipt_email(to: str, receipt: Receipt, sender: User) -> None:
    """Render the receipt to PDF and email it to ``to`` on behalf of ``sender``."""
    pdf_bytes = render_pdf(receipt)
    msg = _build_message(to, receipt, pdf_bytes, sender)

    if not settings.smtp_host:
        # Dev fallback: log instead of sending.
        logger.info(
            "EMAIL (dev, not sent) -> %s | subject=%r | attachment=%s (%d bytes)",
            to,
            msg["Subject"],
            receipt_filename(receipt, "pdf"),
            len(pdf_bytes),
        )
        return

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_user or None,
        password=settings.smtp_password or None,
        start_tls=settings.smtp_tls,
    )
    logger.info("Receipt email sent to %s", to)

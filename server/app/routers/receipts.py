"""Receipts — the public infrastructure layer + the account-gated e-invoice tools.

Two tiers (the spine of the MVP):

* **Anyone, no login** — open a receipt by its URL, and download the human-readable
  **PDF / PNG**. This is "no app, no scanning, no account": tap the NFC tile or the
  online link and the receipt is just *there* in the browser.
* **Logged-in account holders** — additionally export the **structured JSON** and the
  **EN 16931 UBL** e-invoice, **email** the receipt to themselves, and **send it to
  their accountant** (PDF + UBL). A compliant e-invoice needs a *buyer* identity, so
  these legitimately require an account. The first such action also **links** the
  receipt to that user (``user_id``), so it shows up under their expenses.
"""

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth import CurrentUser, OptionalUser
from app.database import get_session
from app.einvoice import receipt_to_einvoice_dict
from app.email import send_receipt_email
from app.models import CreditNote, EmailRequest, Receipt, ReceiptOut, ReceiptStatus, User
from app.pdf import download_headers, receipt_filename, render_pdf, render_png
from app.ubl import UblComplianceError, render_ubl

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_receipt(invoice_id: str, session: AsyncSession) -> Receipt:
    receipt = await session.get(Receipt, invoice_id)
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receipt not found")
    return receipt


def _link_to_user(receipt: Receipt, user: User) -> None:
    """Claim an ownerless receipt for the acting user (so it becomes their expense)."""
    if receipt.user_id is None:
        receipt.user_id = user.id


def _ubl_or_422(receipt: Receipt, user: User) -> bytes:
    try:
        return render_ubl(receipt, buyer=user)
    except UblComplianceError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))


# --------------------------------------------------------------------------- #
# Public — view + human-readable downloads (no login)
# --------------------------------------------------------------------------- #
@router.get("", response_model=list[ReceiptOut])
async def list_receipts(user: CurrentUser, session: SessionDep) -> list[Receipt]:
    """List **only the caller's own** receipts (privacy: never expose other users'
    receipts). Requires an account; receipts link to the account on checkout (when
    logged in) and on view/export/email/refund."""
    result = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .order_by(Receipt.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt(invoice_id: str, user: CurrentUser, session: SessionDep) -> Response:
    """Delete a receipt from the caller's account.

    Owner-only: you can only delete a receipt linked to *your* account (404 hides
    other users' receipts). A linked credit note is removed with it. The original
    public receipt is the user's own expense record, so deleting it is their call.
    """
    receipt = await _get_receipt(invoice_id, session)
    if receipt.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receipt not found")
    if receipt.credit_note_id:
        cn = await session.get(CreditNote, receipt.credit_note_id)
        if cn is not None:
            await session.delete(cn)  # remove the FK child first
    await session.delete(receipt)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{invoice_id}", response_model=ReceiptOut)
async def get_receipt(invoice_id: str, user: OptionalUser, session: SessionDep) -> Receipt:
    receipt = await _get_receipt(invoice_id, session)
    # A logged-in viewer claims an ownerless receipt (capability URL → "it's mine"),
    # so it shows up under their account.
    if user is not None:
        _link_to_user(receipt, user)
    # Demo telemetry: first open flips GENERATED -> VIEWED. Never downgrade SENT/REFUNDED.
    if receipt.status == ReceiptStatus.GENERATED.value:
        receipt.status = ReceiptStatus.VIEWED.value
    return receipt


@router.get("/{invoice_id}/pdf")
async def download_pdf(invoice_id: str, session: SessionDep) -> Response:
    receipt = await _get_receipt(invoice_id, session)
    return Response(
        content=render_pdf(receipt),
        media_type="application/pdf",
        headers=download_headers(receipt_filename(receipt, "pdf")),
    )


@router.get("/{invoice_id}/png")
async def download_png(invoice_id: str, session: SessionDep) -> Response:
    receipt = await _get_receipt(invoice_id, session)
    return Response(
        content=render_png(receipt),
        media_type="image/png",
        headers=download_headers(receipt_filename(receipt, "png")),
    )


# --------------------------------------------------------------------------- #
# Account-gated — structured exports + email (login required)
# --------------------------------------------------------------------------- #
@router.get("/{invoice_id}/json")
async def download_json(invoice_id: str, user: CurrentUser, session: SessionDep) -> Response:
    receipt = await _get_receipt(invoice_id, session)
    _link_to_user(receipt, user)
    body = json.dumps(receipt_to_einvoice_dict(receipt, buyer=user), indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers=download_headers(receipt_filename(receipt, "json")),
    )


@router.get("/{invoice_id}/ubl")
async def download_ubl(invoice_id: str, user: CurrentUser, session: SessionDep) -> Response:
    receipt = await _get_receipt(invoice_id, session)
    receipt.buyer_name = f"{user.first_name} {user.last_name}".strip()
    receipt.buyer_email = user.email
    _link_to_user(receipt, user)
    content = _ubl_or_422(receipt, user)
    return Response(
        content=content,
        media_type="application/xml",
        headers=download_headers(receipt_filename(receipt, "xml")),
    )


async def _email_receipt(invoice_id: str, to: str, user: User, session: AsyncSession) -> dict:
    receipt = await _get_receipt(invoice_id, session)
    receipt.buyer_name = f"{user.first_name} {user.last_name}".strip()
    receipt.buyer_email = user.email
    _link_to_user(receipt, user)
    # send_receipt_email builds the UBL too; surface compliance errors as 422.
    try:
        result = await send_receipt_email(to, receipt, buyer=user)
    except UblComplianceError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    now = datetime.now(timezone.utc)
    receipt.sent_at = now
    if to == user.email:
        receipt.sent_to_user_email = to
    else:
        receipt.sent_to_accountant_email = to
    if receipt.status != ReceiptStatus.REFUNDED.value:
        receipt.status = ReceiptStatus.SENT.value
    return {"detail": f"Receipt {receipt.invoice_id} sent to {to}", "delivery": result}


@router.post("/{invoice_id}/email")
async def email_to_self(
    invoice_id: str, body: EmailRequest, user: CurrentUser, session: SessionDep
) -> dict:
    """Email the receipt (PDF + UBL) to the logged-in user (or an override address).

    Refuses to send twice: once a receipt has been emailed to the user it can't be
    re-sent (prevents duplicate copies in their inbox / bookkeeping)."""
    receipt = await _get_receipt(invoice_id, session)
    if receipt.sent_to_user_email:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This receipt was already emailed to {receipt.sent_to_user_email}.",
        )
    to = body.to or user.email
    return await _email_receipt(invoice_id, to, user, session)


@router.post("/{invoice_id}/send-to-accountant")
async def send_to_accountant(
    invoice_id: str, user: CurrentUser, session: SessionDep
) -> dict:
    """Forward the receipt (PDF + UBL) to the accountant configured on the account.

    Refuses to send twice: once a receipt has been sent to the accountant it can't
    be sent again (a single, auditable copy in their books)."""
    if not user.accountant_email:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No accountant email on file — add one on your account page.",
        )
    receipt = await _get_receipt(invoice_id, session)
    if receipt.sent_to_accountant_email:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"This receipt was already sent to {receipt.sent_to_accountant_email}.",
        )
    return await _email_receipt(invoice_id, user.accountant_email, user, session)

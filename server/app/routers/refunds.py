"""Refunds / returns — modeled as linked **credit notes**.

Addresses the lecturer's feedback head-on: in real financial administration a
refund must *never* erase the original receipt. ZZPay keeps the original receipt
exactly as it was and issues a separate :class:`~app.models.CreditNote` that
references it (UBL ``BillingReference``). The correction stays auditable, and if the
original was already emailed to the accountant we flag that so the credit note can
follow the same way.

Tiering mirrors receipts: requesting a refund + downloading the credit-note PDF/PNG
is public (demo-friendly); the structured JSON/UBL export and emailing require an
account (buyer identity for a compliant e-invoice).
"""

import json
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, OptionalUser
from app.database import get_session
from app.einvoice import credit_from_receipt, credit_note_to_einvoice_dict
from app.email import send_credit_note_email
from app.models import (
    CreditNote,
    CreditNoteOut,
    CreditNoteStatus,
    EmailRequest,
    Receipt,
    ReceiptStatus,
    RefundRequest,
    RefundResponse,
    next_credit_note_id,
)
from app.pdf import (
    credit_note_filename,
    download_headers,
    render_credit_note_pdf,
    render_credit_note_png,
)
from app.ubl import UblComplianceError, render_credit_note_ubl

router = APIRouter(prefix="/api", tags=["refunds"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _get_receipt(invoice_id: str, session: AsyncSession) -> Receipt:
    receipt = await session.get(Receipt, invoice_id)
    if receipt is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receipt not found")
    return receipt


async def _get_credit_note(credit_note_id: str, session: AsyncSession) -> CreditNote:
    cn = await session.get(CreditNote, credit_note_id)
    if cn is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Credit note not found")
    return cn


@router.post("/receipts/{invoice_id}/refund", response_model=RefundResponse,
             status_code=status.HTTP_201_CREATED)
async def create_refund(
    invoice_id: str, body: RefundRequest, user: OptionalUser, session: SessionDep
) -> RefundResponse:
    """Create a linked credit note for the chosen line(s). Original receipt untouched.

    If the caller is a logged-in account holder with an accountant configured, the
    new credit note is **automatically emailed to that accountant** (PDF + UBL), so
    the correction reaches the books without a second manual step.
    """
    receipt = await _get_receipt(invoice_id, session)
    if receipt.status == ReceiptStatus.REFUNDED.value:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "This receipt already has a linked credit note.")
    if not body.full and not body.line_ids:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Specify line_ids to refund, or set full=true.")

    # Whether the original had already gone to the accountant (for the warning).
    was_sent_to_accountant = bool(receipt.sent_to_accountant_email)

    cn_id = await next_credit_note_id(session)
    try:
        cn = credit_from_receipt(
            receipt, cn_id, full=body.full, line_ids=body.line_ids, reason=body.reason
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))

    if user is not None:
        cn.user_id = user.id
        if receipt.user_id is None:
            receipt.user_id = user.id

    receipt.status = ReceiptStatus.REFUNDED.value
    receipt.credit_note_id = cn_id

    # Auto-forward the credit note to the accountant (logged-in + configured).
    emailed_to = None
    if user is not None and user.accountant_email:
        try:
            await send_credit_note_email(user.accountant_email, cn, receipt, buyer=user)
        except UblComplianceError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
        cn.status = CreditNoteStatus.SENT.value
        cn.sent_to_accountant_email = user.accountant_email
        cn.sent_at = datetime.now(timezone.utc)
        emailed_to = user.accountant_email

    session.add(cn)
    await session.flush()

    warning = None
    if was_sent_to_accountant:
        warning = (
            "This receipt was already sent to your accountant. ZZPay created a "
            "linked credit note so the correction remains auditable."
        )
    return RefundResponse(
        credit_note=CreditNoteOut.model_validate(cn, from_attributes=True),
        warning=warning,
        credit_note_emailed_to=emailed_to,
    )


# --------------------------------------------------------------------------- #
# Credit note — public view + PDF/PNG; gated JSON/UBL/email
# --------------------------------------------------------------------------- #
@router.get("/credit-notes/{credit_note_id}", response_model=CreditNoteOut)
async def get_credit_note(credit_note_id: str, session: SessionDep) -> CreditNote:
    return await _get_credit_note(credit_note_id, session)


@router.get("/credit-notes/{credit_note_id}/pdf")
async def credit_note_pdf(credit_note_id: str, session: SessionDep) -> Response:
    cn = await _get_credit_note(credit_note_id, session)
    original = await _get_receipt(cn.original_receipt_id, session)
    return Response(
        content=render_credit_note_pdf(cn, original),
        media_type="application/pdf",
        headers=download_headers(credit_note_filename(cn, "pdf")),
    )


@router.get("/credit-notes/{credit_note_id}/png")
async def credit_note_png(credit_note_id: str, session: SessionDep) -> Response:
    cn = await _get_credit_note(credit_note_id, session)
    original = await _get_receipt(cn.original_receipt_id, session)
    return Response(
        content=render_credit_note_png(cn, original),
        media_type="image/png",
        headers=download_headers(credit_note_filename(cn, "png")),
    )


@router.get("/credit-notes/{credit_note_id}/json")
async def credit_note_json(
    credit_note_id: str, user: CurrentUser, session: SessionDep
) -> Response:
    cn = await _get_credit_note(credit_note_id, session)
    body = json.dumps(credit_note_to_einvoice_dict(cn, buyer=user), indent=2)
    return Response(
        content=body,
        media_type="application/json",
        headers=download_headers(credit_note_filename(cn, "json")),
    )


@router.get("/credit-notes/{credit_note_id}/ubl")
async def credit_note_ubl(
    credit_note_id: str, user: CurrentUser, session: SessionDep
) -> Response:
    cn = await _get_credit_note(credit_note_id, session)
    original = await _get_receipt(cn.original_receipt_id, session)
    try:
        content = render_credit_note_ubl(cn, buyer=user, seller=original)
    except UblComplianceError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return Response(
        content=content,
        media_type="application/xml",
        headers=download_headers(credit_note_filename(cn, "xml")),
    )


@router.post("/credit-notes/{credit_note_id}/email")
async def email_credit_note(
    credit_note_id: str, body: EmailRequest, user: CurrentUser, session: SessionDep
) -> dict:
    """Email the credit note (PDF + UBL) to the user or their accountant."""
    cn = await _get_credit_note(credit_note_id, session)
    original = await _get_receipt(cn.original_receipt_id, session)

    if body.target == "accountant":
        if not user.accountant_email:
            raise HTTPException(status.HTTP_400_BAD_REQUEST,
                                "No accountant email on file — add one on your account page.")
        if cn.sent_to_accountant_email:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"This credit note was already sent to {cn.sent_to_accountant_email}.")
        to = body.to or user.accountant_email
    else:
        if cn.sent_to_user_email:
            raise HTTPException(status.HTTP_409_CONFLICT,
                                f"This credit note was already emailed to {cn.sent_to_user_email}.")
        to = body.to or user.email

    try:
        result = await send_credit_note_email(to, cn, original, buyer=user)
    except UblComplianceError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    now = datetime.now(timezone.utc)
    cn.sent_at = now
    if to == user.accountant_email:
        cn.sent_to_accountant_email = to
    else:
        cn.sent_to_user_email = to
    cn.status = CreditNoteStatus.SENT.value
    return {"detail": f"Credit note {cn.credit_note_id} sent to {to}", "delivery": result}

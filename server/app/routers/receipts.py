"""Receipts: the user's bonnetjes, plus download (PDF/PNG) and email delivery.

Every endpoint is scoped to the authenticated user — ownership is enforced
server-side, never trusting the client to say which receipts are "theirs".
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.auth import CurrentUser
from app.database import get_session
from app.email import send_receipt_email
from app.models import (
    EmailReceiptRequest,
    Receipt,
    ReceiptCreate,
    ReceiptOut,
    User,
)
from app.pdf import receipt_filename, render_pdf, render_png

router = APIRouter(prefix="/api/receipts", tags=["receipts"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def _owned_receipt(receipt_id: UUID, user: User, session: AsyncSession) -> Receipt:
    """Load a receipt and 404 if it doesn't exist or isn't the caller's."""
    receipt = await session.get(Receipt, receipt_id)
    if receipt is None or receipt.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Receipt not found")
    return receipt


@router.get("", response_model=list[ReceiptOut])
async def list_receipts(user: CurrentUser, session: SessionDep) -> list[Receipt]:
    result = await session.execute(
        select(Receipt)
        .where(Receipt.user_id == user.id)
        .order_by(Receipt.purchased_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{receipt_id}", response_model=ReceiptOut)
async def get_receipt(receipt_id: UUID, user: CurrentUser, session: SessionDep) -> Receipt:
    return await _owned_receipt(receipt_id, user, session)


@router.post("", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
async def create_receipt(
    body: ReceiptCreate, user: CurrentUser, session: SessionDep
) -> Receipt:
    """Manual / mock receipt creation — the v1 ingestion path.

    In production this is where a merchant's till (via the NFC tap) would POST
    the transaction; for the MVP we accept the same structured payload directly.
    """
    receipt = Receipt(
        user_id=user.id,
        merchant_name=body.merchant_name,
        merchant_vat=body.merchant_vat,
        purchased_at=body.purchased_at,
        total_amount=body.total_amount,
        vat_amount=body.vat_amount,
        currency=body.currency,
        line_items=[item.model_dump(mode="json") for item in body.line_items],
    )
    session.add(receipt)
    await session.flush()
    return receipt


@router.get("/{receipt_id}/pdf")
async def download_pdf(receipt_id: UUID, user: CurrentUser, session: SessionDep) -> Response:
    receipt = await _owned_receipt(receipt_id, user, session)
    return Response(
        content=render_pdf(receipt),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{receipt_filename(receipt, "pdf")}"'},
    )


@router.get("/{receipt_id}/png")
async def download_png(receipt_id: UUID, user: CurrentUser, session: SessionDep) -> Response:
    receipt = await _owned_receipt(receipt_id, user, session)
    return Response(
        content=render_png(receipt),
        media_type="image/png",
        headers={"Content-Disposition": f'attachment; filename="{receipt_filename(receipt, "png")}"'},
    )


@router.post("/{receipt_id}/email")
async def email_receipt(
    receipt_id: UUID,
    body: EmailReceiptRequest,
    user: CurrentUser,
    session: SessionDep,
) -> dict:
    """Email the receipt PDF. Defaults to the user, or their accountant."""
    receipt = await _owned_receipt(receipt_id, user, session)

    to = body.to
    if to is None:
        if body.target == "accountant":
            if not user.accountant_email:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "No accountant email on file — add one on your account page.",
                )
            to = user.accountant_email
        else:
            to = user.email

    await send_receipt_email(to, receipt, sender=user)
    return {"detail": f"Receipt sent to {to}"}

"""Merchant checkout — the *source* where a structured receipt is created.

In production this is the merchant's point-of-sale system: when the customer pays,
the till POSTs the basket to ZZPay and gets back a structured, EN 16931-compatible
receipt plus a delivery URL (written to an NFC tile, shown as a QR/online link, …).

For the MVP we simulate the POS with a small registry of demo merchants/baskets so
the whole flow can be demoed without real hardware. Prices are VAT-inclusive
consumer prices, exactly as printed at a Dutch till.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import OptionalUser
from app.database import get_session
from app.einvoice import basket_to_receipt, q
from app.models import (
    BasketLine,
    CheckoutRequest,
    Channel,
    Receipt,
    ReceiptOut,
    next_invoice_id,
)

router = APIRouter(prefix="/api/checkout", tags=["checkout"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Single source of truth for the demo merchants. seed.py imports this too, so the
# seeded receipts and the live "Generate" button always agree.
MERCHANTS: dict[str, dict] = {
    "bouwmaat": {
        "name": "Bouwmaat Rotterdam",
        "vat": "NL123456789B01",
        "address": "Rotterdam, Netherlands",
        "country": "NL",
        "default_channel": Channel.NFC,
        "basket": [
            BasketLine(description="Schroeven", quantity=2, unit_price="6.00"),
            BasketLine(description="Houtplaat", quantity=1, unit_price="25.00"),
            BasketLine(description="Kit", quantity=1, unit_price="8.98"),
        ],
    },
    "shell": {
        "name": "Shell Den Haag",
        "vat": "NL987654321B01",
        "address": "Den Haag, Netherlands",
        "country": "NL",
        "default_channel": Channel.ONLINE_LINK,
        "basket": [
            BasketLine(description="Diesel", quantity=1, unit_price="78.00"),
            BasketLine(description="Ruitensproeiervloeistof", quantity=1, unit_price="8.20"),
        ],
    },
}


def _basket_preview(merchant: dict) -> dict:
    """Shape a merchant entry for the demo UI (with a gross total preview)."""
    total = q(sum(Decimal(str(l.quantity)) * l.unit_price for l in merchant["basket"]))
    return {
        "name": merchant["name"],
        "vat": merchant["vat"],
        "address": merchant["address"],
        "default_channel": merchant["default_channel"].value,
        "lines": [
            {
                "description": l.description,
                "quantity": l.quantity,
                "unit_price": str(l.unit_price),
                "vat_rate": str(l.vat_rate),
            }
            for l in merchant["basket"]
        ],
        "preview_total": str(total),
    }


@router.get("/demo-baskets")
async def demo_baskets() -> dict:
    """The hardcoded demo merchants/baskets used by the /merchant and /online pages."""
    return {key: _basket_preview(m) for key, m in MERCHANTS.items()}


@router.post("", response_model=ReceiptOut, status_code=status.HTTP_201_CREATED)
async def checkout(body: CheckoutRequest, user: OptionalUser, session: SessionDep) -> Receipt:
    """Turn a merchant basket into a structured receipt (the one-click moment).

    Mints a human-readable ``invoice_id``, maps the basket into an EN 16931-shaped
    Receipt, and returns it with a ``delivery_url`` (what an NFC tile / online link
    would point at). If the caller is logged in, the receipt is linked to their
    account so it appears under their receipts.
    """
    merchant = MERCHANTS.get(body.merchant_key)
    if merchant is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown merchant")

    invoice_id = await next_invoice_id(session)
    receipt = basket_to_receipt(merchant, merchant["basket"], body.channel, invoice_id)
    if user is not None:
        receipt.user_id = user.id
    session.add(receipt)
    await session.flush()  # commit happens in get_session on success
    return receipt

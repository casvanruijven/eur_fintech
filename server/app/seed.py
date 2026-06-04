"""Seed demo data on first run so the UI (and the lecturer) have something to open.

Idempotent: keyed on the canonical receipt ``ZZP-2026-0001``. Seeds:

* a demo **account** (``demo@zzpay.nl`` / ``demo1234``) with an accountant email —
  used to demo the structured export + "send to accountant" flow;
* ``ZZP-2026-0001`` — Bouwmaat (NFC), already **REFUNDED** via ``CN-2026-0001``
  (the returned "Kit" line, −€8.98) so the refund example works out of the box;
* ``ZZP-2026-0002`` — Shell (online link), to show multi-channel.

Receipts are seeded **ownerless** (``user_id = None``) to mirror reality — a
merchant creates them at checkout; they only link to the demo user once that user
exports/emails one.
"""

import logging

from app.auth import hash_password
from app.database import async_session
from app.einvoice import basket_to_receipt, credit_from_receipt
from app.models import Channel, CreditNote, Receipt, ReceiptStatus, User
from app.routers.checkout import MERCHANTS

logger = logging.getLogger("zzpay.seed")

DEMO_EMAIL = "demo@zzpay.nl"
DEMO_PASSWORD = "demo1234"
DEMO_ACCOUNTANT = "accountant@demo-accounting.nl"


async def run() -> None:
    async with async_session() as session:
        if await session.get(Receipt, "ZZP-2026-0001") is not None:
            return

        # Demo account (optional path: accountant forwarding + structured export).
        user = User(
            email=DEMO_EMAIL,
            first_name="Demo",
            last_name="ZZP'er",
            password_hash=hash_password(DEMO_PASSWORD),
            accountant_email=DEMO_ACCOUNTANT,
            # Business identity → fills the EN 16931 buyer party in UBL/JSON exports.
            company_name="Demo ZZP Diensten",
            vat_number="NL002233445B01",
            kvk_number="87654321",
            street="Coolsingel 1",
            postal_code="3011 AD",
            city="Rotterdam",
            country="NL",
        )
        session.add(user)

        # ZZP-2026-0001 — Bouwmaat, NFC; ZZP-2026-0002 — Shell, online link.
        bouwmaat = basket_to_receipt(
            MERCHANTS["bouwmaat"], MERCHANTS["bouwmaat"]["basket"],
            Channel.NFC, "ZZP-2026-0001",
        )
        kit_line = next(l for l in bouwmaat.invoice_lines if l["description"] == "Kit")
        shell = basket_to_receipt(
            MERCHANTS["shell"], MERCHANTS["shell"]["basket"],
            Channel.ONLINE_LINK, "ZZP-2026-0002",
        )
        session.add(bouwmaat)
        session.add(shell)
        # Flush the receipts so the rows exist before the credit note's FK is checked
        # (there is no ORM relationship to order the inserts for us, and Postgres
        # enforces the foreign key immediately).
        await session.flush()

        # Refund the "Kit" line of ZZP-2026-0001 -> linked credit note CN-2026-0001.
        cn = credit_from_receipt(
            bouwmaat, "CN-2026-0001",
            line_ids=[kit_line["id"]],
            reason="Customer returned unused item",
        )
        bouwmaat.status = ReceiptStatus.REFUNDED.value
        bouwmaat.credit_note_id = "CN-2026-0001"
        session.add(cn)

        await session.commit()
        logger.info(
            "Seeded demo data: account %s / %s, receipts ZZP-2026-0001 (refunded), "
            "ZZP-2026-0002", DEMO_EMAIL, DEMO_PASSWORD,
        )

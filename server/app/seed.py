"""Seed a demo account + sample receipts on first run, so the UI has content.

Idempotent: if the demo user already exists, this does nothing.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlmodel import select

from app.auth import hash_password
from app.database import async_session
from app.models import Receipt, User

logger = logging.getLogger("zzpay.seed")

DEMO_EMAIL = "demo@zzpay.nl"
DEMO_PASSWORD = "demo1234"


def _sample_receipts(user_id) -> list[Receipt]:
    now = datetime.now(timezone.utc)
    return [
        Receipt(
            user_id=user_id,
            merchant_name="Albert Heijn",
            merchant_vat="NL001234567B01",
            purchased_at=now - timedelta(days=1, hours=3),
            total_amount=Decimal("23.45"),
            vat_amount=Decimal("2.13"),
            line_items=[
                {"description": "Koffiebonen 1kg", "quantity": 1, "unit_price": 12.99},
                {"description": "Havermelk", "quantity": 2, "unit_price": 1.79},
                {"description": "Volkorenbrood", "quantity": 1, "unit_price": 2.49},
            ],
        ),
        Receipt(
            user_id=user_id,
            merchant_name="Shell Station Rotterdam",
            merchant_vat="NL009876543B01",
            purchased_at=now - timedelta(days=4, hours=8),
            total_amount=Decimal("78.20"),
            vat_amount=Decimal("13.57"),
            line_items=[{"description": "Euro 95 (42.1 L)", "quantity": 1, "unit_price": 78.20}],
        ),
        Receipt(
            user_id=user_id,
            merchant_name="Coffee & Co",
            purchased_at=now - timedelta(hours=5),
            total_amount=Decimal("4.50"),
            vat_amount=Decimal("0.41"),
            line_items=[{"description": "Cappuccino", "quantity": 1, "unit_price": 4.50}],
        ),
    ]


async def run() -> None:
    async with async_session() as session:
        existing = await session.execute(select(User).where(User.email == DEMO_EMAIL))
        if existing.scalar_one_or_none() is not None:
            return

        user = User(
            email=DEMO_EMAIL,
            first_name="Demo",
            last_name="ZZP'er",
            password_hash=hash_password(DEMO_PASSWORD),
            accountant_email="accountant@example.com",
        )
        session.add(user)
        await session.flush()

        for receipt in _sample_receipts(user.id):
            session.add(receipt)
        await session.commit()

        logger.info(
            "Seeded demo account -> email=%s password=%s (%d sample receipts)",
            DEMO_EMAIL,
            DEMO_PASSWORD,
            3,
        )

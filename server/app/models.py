"""Database tables (SQLModel) and the request/response schemas (Pydantic).

Two entities only — User and Receipt — which is the whole data model of the MVP.
The conceptual innovation ("turn a transaction into clean, structured data") lives
in the Receipt model: every field is typed, and line items are structured JSON.
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr
from sqlalchemy import JSON, Column, DateTime, Numeric
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
class User(SQLModel, table=True):
    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    first_name: str
    last_name: str
    password_hash: str
    # Where receipts should be forwarded automatically. Optional.
    accountant_email: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )


class Receipt(SQLModel, table=True):
    __tablename__ = "receipts"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="users.id", index=True)

    merchant_name: str
    merchant_vat: str | None = Field(default=None)
    purchased_at: datetime = Field(sa_type=DateTime(timezone=True))
    total_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    vat_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    currency: str = Field(default="EUR")
    # [{description, quantity, unit_price}, ...]
    line_items: list[dict] = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )


# --------------------------------------------------------------------------- #
# Schemas — Users
# --------------------------------------------------------------------------- #
class UserCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    password: str = Field(min_length=8)
    accountant_email: EmailStr | None = None


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    accountant_email: EmailStr | None = None


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    accountant_email: EmailStr | None = None
    created_at: datetime


# --------------------------------------------------------------------------- #
# Schemas — Receipts
# --------------------------------------------------------------------------- #
class LineItem(BaseModel):
    description: str
    quantity: float = 1
    unit_price: Decimal


class ReceiptCreate(BaseModel):
    merchant_name: str
    merchant_vat: str | None = None
    purchased_at: datetime
    total_amount: Decimal
    vat_amount: Decimal
    currency: str = "EUR"
    line_items: list[LineItem] = []


class ReceiptOut(BaseModel):
    id: UUID
    merchant_name: str
    merchant_vat: str | None
    purchased_at: datetime
    total_amount: Decimal
    vat_amount: Decimal
    currency: str
    line_items: list[dict]
    created_at: datetime


class EmailReceiptRequest(BaseModel):
    # Where to send. If omitted, defaults to the recipient implied by ``target``.
    to: EmailStr | None = None
    # "self" -> the logged-in user's email, "accountant" -> their accountant_email.
    target: str = "self"

"""Database tables (SQLModel) and the request/response schemas (Pydantic).

The data model is the heart of ZZPay's conceptual innovation: a checkout basket
is turned into a clean, structured, **EN 16931 / UBL-inspired** receipt object at
the source — no scanning, no OCR. Three entities:

* ``User``       — an *optional* account that stores the accountant email and lets
                   a returning ZZP'er be remembered (JWT). Receipts are public and
                   only *link* to a user once that user acts on them.
* ``Receipt``    — the structured e-invoice. Created by a merchant at checkout,
                   keyed by a human-readable ``invoice_id`` (e.g. ``ZZP-2026-0001``).
* ``CreditNote`` — a *linked* correction document for refunds/returns. The original
                   receipt is never deleted or mutated — auditability by design.

Money uses ``Decimal``/``Numeric(10, 2)``; in JSON we serialise decimals as strings
to avoid binary-float drift. Timestamps are timezone-aware UTC.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr
from sqlalchemy import JSON, Column, DateTime, Numeric
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, func, select


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class Channel(str, Enum):
    """Delivery channel. NFC is *one* channel; the receipt object is identical
    regardless of how it reaches the customer (multi-channel infrastructure)."""

    NFC = "NFC"
    ONLINE_LINK = "ONLINE_LINK"


class ReceiptStatus(str, Enum):
    GENERATED = "GENERATED"  # just created at checkout
    VIEWED = "VIEWED"        # customer opened the public page
    SENT = "SENT"            # emailed to the user and/or accountant
    REFUNDED = "REFUNDED"    # a linked credit note exists


class CreditNoteStatus(str, Enum):
    GENERATED = "GENERATED"
    SENT = "SENT"


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
class User(SQLModel, table=True):
    """Optional account. Its job is to remember the accountant email and to let a
    returning user be recognised (JWT cookie). Receipts are NOT owned through it —
    a receipt only links to a user once that user exports/emails it."""

    __tablename__ = "users"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(index=True, unique=True)
    first_name: str
    last_name: str
    password_hash: str
    # Where receipts should be forwarded. Configured on the account page.
    accountant_email: str | None = Field(default=None)

    # Business / billing identity — the fields that normally appear on a business
    # invoice. They become the EN 16931 *buyer party* in the UBL + JSON exports, so
    # the structured e-invoice carries the ZZP'er's real company details.
    company_name: str | None = Field(default=None)
    vat_number: str | None = Field(default=None)      # buyer BTW-nummer (BT-48)
    kvk_number: str | None = Field(default=None)      # buyer registration id (BT-47)
    street: str | None = Field(default=None)          # BT-50
    postal_code: str | None = Field(default=None)     # BT-53
    city: str | None = Field(default=None)            # BT-52
    country: str = Field(default="NL")                # BT-55

    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )


class Receipt(SQLModel, table=True):
    """A structured, EN 16931-inspired receipt (purchase invoice).

    Flat typed columns per the project's "keep it simple" convention; only the
    variable-length ``invoice_lines`` is JSON. ``invoice_id`` is the primary key
    *and* the public URL slug (``/receipt/ZZP-2026-0001``).
    """

    __tablename__ = "receipts"

    invoice_id: str = Field(primary_key=True)  # "ZZP-2026-0001"

    # Nullable: receipts are created ownerless at the merchant checkout and only
    # link to a user the first time that (logged-in) user exports/emails them.
    user_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)

    issue_date: str           # ISO date "2026-06-04" (UBL IssueDate is a date)
    issue_time: str           # "14:32:05"
    currency: str = Field(default="EUR")
    channel: str              # Channel value

    # Seller / AccountingSupplierParty
    supplier_name: str
    supplier_vat: str | None = Field(default=None)
    supplier_address: str
    supplier_country: str = Field(default="NL")

    # Buyer snapshot / AccountingCustomerParty (overridden by the linked user at
    # UBL time, where a real name + identity are required by EN 16931).
    buyer_name: str = Field(default="Guest user")
    buyer_email: str | None = Field(default=None)

    # [{id, description, quantity, unit_price, vat_rate, line_extension_amount,
    #   line_tax_total}, ...] — decimals stored as strings.
    invoice_lines: list[dict] = Field(default_factory=list, sa_column=Column(JSON))

    # LegalMonetaryTotal / TaxTotal
    line_extension_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    tax_exclusive_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    tax_inclusive_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    payable_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    tax_total: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    delivery_url: str
    status: str = Field(default=ReceiptStatus.GENERATED.value)

    # Delivery status (mock email). Flattened instead of a nested JSON "sent_to".
    sent_to_user_email: str | None = Field(default=None)
    sent_to_accountant_email: str | None = Field(default=None)
    sent_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    # Back-link to a refund correction, if any.
    credit_note_id: str | None = Field(default=None)

    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )


class CreditNote(SQLModel, table=True):
    """A linked correction for a refund/return. References the original receipt via
    ``original_receipt_id`` (UBL ``BillingReference``) and never mutates it."""

    __tablename__ = "credit_notes"

    credit_note_id: str = Field(primary_key=True)  # "CN-2026-0001"
    original_receipt_id: str = Field(foreign_key="receipts.invoice_id", index=True)
    user_id: UUID | None = Field(default=None, foreign_key="users.id", index=True)

    issue_date: str
    issue_time: str
    currency: str = Field(default="EUR")

    # Same line shape as a receipt; these are the *credited* (returned) items.
    credited_items: list[dict] = Field(default_factory=list, sa_column=Column(JSON))

    line_extension_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    tax_exclusive_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    tax_inclusive_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    payable_amount: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    tax_total: Decimal = Field(sa_column=Column(Numeric(10, 2), nullable=False))

    reason: str = Field(default="Customer refund")
    status: str = Field(default=CreditNoteStatus.GENERATED.value)

    sent_to_user_email: str | None = Field(default=None)
    sent_to_accountant_email: str | None = Field(default=None)
    sent_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    created_at: datetime = Field(
        default_factory=_utcnow, sa_type=DateTime(timezone=True)
    )


# --------------------------------------------------------------------------- #
# Sequential, human-readable IDs (ZZP-2026-0001 / CN-2026-0001)
# --------------------------------------------------------------------------- #
async def next_invoice_id(session: AsyncSession, year: int | None = None) -> str:
    year = year or _utcnow().year
    count = await session.scalar(select(func.count()).select_from(Receipt))
    return f"ZZP-{year}-{(count or 0) + 1:04d}"


async def next_credit_note_id(session: AsyncSession, year: int | None = None) -> str:
    year = year or _utcnow().year
    count = await session.scalar(select(func.count()).select_from(CreditNote))
    return f"CN-{year}-{(count or 0) + 1:04d}"


# --------------------------------------------------------------------------- #
# Schemas — Users (the optional account)
# --------------------------------------------------------------------------- #
class BusinessDetails(BaseModel):
    """The buyer's business identity (shared by create/update/out)."""

    company_name: str | None = None
    vat_number: str | None = None
    kvk_number: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str = "NL"


class UserCreate(BusinessDetails):
    email: EmailStr
    first_name: str
    last_name: str
    password: str = Field(min_length=8)
    accountant_email: EmailStr | None = None


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    accountant_email: EmailStr | None = None
    company_name: str | None = None
    vat_number: str | None = None
    kvk_number: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    country: str | None = None


class UserOut(BusinessDetails):
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    accountant_email: EmailStr | None = None
    created_at: datetime


# --------------------------------------------------------------------------- #
# Schemas — Checkout / Receipts
# --------------------------------------------------------------------------- #
class BasketLine(BaseModel):
    """A single line as it comes from the (simulated) point-of-sale system."""

    description: str
    quantity: float = 1
    unit_price: Decimal
    vat_rate: Decimal = Decimal("0.21")  # Dutch standard rate


class CheckoutRequest(BaseModel):
    merchant_key: str               # "bouwmaat" | "shell"
    channel: Channel = Channel.NFC


class InvoiceLineOut(BaseModel):
    id: int
    description: str
    quantity: float
    unit_price: Decimal
    vat_rate: Decimal
    line_extension_amount: Decimal
    line_tax_total: Decimal


class ReceiptOut(BaseModel):
    invoice_id: str
    issue_date: str
    issue_time: str
    currency: str
    channel: Channel
    supplier_name: str
    supplier_vat: str | None
    supplier_address: str
    supplier_country: str
    buyer_name: str
    buyer_email: str | None
    invoice_lines: list[InvoiceLineOut]
    line_extension_amount: Decimal
    tax_exclusive_amount: Decimal
    tax_inclusive_amount: Decimal
    payable_amount: Decimal
    tax_total: Decimal
    delivery_url: str
    status: ReceiptStatus
    sent_to_user_email: str | None
    sent_to_accountant_email: str | None
    sent_at: datetime | None
    credit_note_id: str | None
    created_at: datetime


class CreditNoteOut(BaseModel):
    credit_note_id: str
    original_receipt_id: str
    issue_date: str
    issue_time: str
    currency: str
    credited_items: list[InvoiceLineOut]
    line_extension_amount: Decimal
    tax_exclusive_amount: Decimal
    tax_inclusive_amount: Decimal
    payable_amount: Decimal
    tax_total: Decimal
    reason: str
    status: CreditNoteStatus
    sent_to_user_email: str | None
    sent_to_accountant_email: str | None
    sent_at: datetime | None
    created_at: datetime


class RefundResponse(BaseModel):
    credit_note: CreditNoteOut
    # Set when the original receipt had already been emailed to an accountant.
    warning: str | None = None
    # Set when the new credit note was auto-emailed to the accountant.
    credit_note_emailed_to: str | None = None


# --------------------------------------------------------------------------- #
# Schemas — Refund / Email requests
# --------------------------------------------------------------------------- #
class RefundRequest(BaseModel):
    # Either refund everything, or list the line ids to credit.
    full: bool = False
    line_ids: list[int] = []
    reason: str = "Customer returned unused item"


class EmailRequest(BaseModel):
    # Override recipient; if omitted we use the receipt's buyer / the user's email.
    to: EmailStr | None = None
    # "self" -> the logged-in user, "accountant" -> their accountant_email.
    target: str = "self"

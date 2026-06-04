"""EN 16931-core UBL 2.1 e-invoice export.

ZZPay's PDF/PNG are human-readable; bookkeeping software needs *machine-readable*
structured invoices. The EU eInvoicing standard **EN 16931** defines the common
semantic model, bound here to **UBL 2.1** XML. A compliant UBL file imports into
essentially any bookkeeping tool (Moneybird, e-Boekhouden, Exact, …) and is the
foundation for later Peppol auto-send.

Direction = expenses (receipts in): the **merchant is the seller** and the
**logged-in ZZP'er is the buyer**, so each receipt becomes a UBL *purchase
invoice* the ZZP'er can hand to their accountant.

Compliance target: EN 16931 **core** — ``CustomizationID = urn:cen.eu:en16931:2017``,
``InvoiceTypeCode 380`` (``381`` semantics for credit notes). We emit every
mandatory business term and make every calculation rule reconcile. The stricter
**Peppol BIS** profile additionally needs electronic-address endpoints + a
``ProfileID`` (Peppol participant IDs we don't have for arbitrary merchants), so
that is deferred to the Peppol step and documented in ``docs/einvoice-standard.md``.

This is a focused MVP implementation, not a certified Access Point.
"""

from decimal import Decimal
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import CreditNote, Receipt, User

_TEMPLATES = Path(__file__).resolve().parent / "templates"
# autoescape for XML so values like "Coffee & Co" become "Coffee &amp; Co".
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATES)),
    autoescape=select_autoescape(["xml"]),
    trim_blocks=True,
    lstrip_blocks=True,
)


class UblComplianceError(ValueError):
    """Raised when a receipt lacks data that EN 16931 makes mandatory.

    Surfaced by the API as HTTP 422 with a human message, so the user fixes the
    receipt *before* it reaches the accountant — rather than emitting an invalid
    e-invoice silently.
    """


def _rate_pct(rate: str | Decimal) -> str:
    """VAT rate as a percentage string, e.g. '0.21' -> '21.00'."""
    return str((Decimal(rate) * 100).quantize(Decimal("0.01")))


def _tax_subtotals(lines: list[dict]) -> list[dict]:
    """Group lines into one TaxSubtotal per VAT rate (handles multi-rate baskets).

    EN 16931 requires a VAT breakdown per category/rate. Demo baskets are a single
    21% rate -> one subtotal, but grouping keeps the document correct if rates mix.
    """
    groups: dict[str, dict] = {}
    for line in lines:
        rate = str(Decimal(line["vat_rate"]))
        g = groups.setdefault(rate, {"taxable": Decimal("0"), "tax": Decimal("0")})
        g["taxable"] += Decimal(line["line_extension_amount"])
        g["tax"] += Decimal(line["line_tax_total"])
    subtotals = []
    for rate, g in groups.items():
        positive = Decimal(rate) > 0
        subtotals.append({
            "taxable": str(g["taxable"].quantize(Decimal("0.01"))),
            "tax": str(g["tax"].quantize(Decimal("0.01"))),
            "category": "S" if positive else "Z",  # Standard rate / Zero rated
            "percent": _rate_pct(rate),
        })
    return subtotals


def _common_context(buyer: User, seller_name: str, seller_vat: str | None,
                    seller_country: str) -> dict:
    if not seller_vat:
        # BR-CO-26: the seller must be identifiable. We carry the seller VAT (BT-31);
        # without it the document cannot satisfy core seller identification.
        raise UblComplianceError(
            "Seller VAT number is missing — required for a valid EN 16931 e-invoice."
        )
    buyer_name = f"{buyer.first_name} {buyer.last_name}".strip() or buyer.email
    return {
        "customization_id": "urn:cen.eu:en16931:2017",
        "seller_name": seller_name,
        "seller_vat": seller_vat,
        "seller_country": seller_country,
        "buyer_name": buyer_name,
        "buyer_country": "NL",  # Dutch app/UI; a real address field is a later step.
    }


def render_ubl(receipt: Receipt, buyer: User) -> bytes:
    """Render a receipt to an EN 16931-core UBL ``<Invoice>`` (UTF-8 bytes)."""
    ctx = _common_context(
        buyer, receipt.supplier_name, receipt.supplier_vat, receipt.supplier_country
    )
    ctx.update({
        "invoice_id": receipt.invoice_id,
        "issue_date": receipt.issue_date,
        "currency": receipt.currency,
        "lines": [
            {
                "id": l["id"],
                "quantity": l["quantity"],
                "description": l["description"],
                "name": l["description"],
                "net": l["line_extension_amount"],
                "category": "S" if Decimal(l["vat_rate"]) > 0 else "Z",
                "percent": _rate_pct(l["vat_rate"]),
                "unit_price": l["line_extension_amount"]
                if float(l["quantity"]) == 0
                else str((Decimal(l["line_extension_amount"]) / Decimal(str(l["quantity"])))
                         .quantize(Decimal("0.0001"))),
            }
            for l in receipt.invoice_lines
        ],
        "tax_subtotals": _tax_subtotals(receipt.invoice_lines),
        "tax_total": str(receipt.tax_total),
        "line_extension_amount": str(receipt.line_extension_amount),
        "tax_exclusive_amount": str(receipt.tax_exclusive_amount),
        "tax_inclusive_amount": str(receipt.tax_inclusive_amount),
        # Paid-receipt trick: the customer already paid at the till, so the whole
        # amount is prepaid and nothing is "due". This also keeps us clear of the
        # rule requiring payment terms/due-date whenever PayableAmount > 0.
        "prepaid_amount": str(receipt.tax_inclusive_amount),
        "payable_amount": "0.00",
    })
    return _env.get_template("invoice_ubl.xml").render(**ctx).encode("utf-8")


def render_credit_note_ubl(cn: CreditNote, buyer: User, seller: Receipt) -> bytes:
    """Render a credit note to an EN 16931-core UBL ``<CreditNote>`` (UTF-8 bytes).

    ``seller`` is the original receipt — its supplier identifies the seller and its
    ``invoice_id`` is referenced via ``cac:BillingReference`` (the correction link).
    """
    ctx = _common_context(
        buyer, seller.supplier_name, seller.supplier_vat, seller.supplier_country
    )
    ctx.update({
        "credit_note_id": cn.credit_note_id,
        "original_receipt_id": cn.original_receipt_id,
        "issue_date": cn.issue_date,
        "currency": cn.currency,
        "reason": cn.reason,
        "lines": [
            {
                "id": l["id"],
                "quantity": l["quantity"],
                "description": l["description"],
                "name": l["description"],
                "net": l["line_extension_amount"],
                "category": "S" if Decimal(l["vat_rate"]) > 0 else "Z",
                "percent": _rate_pct(l["vat_rate"]),
                "unit_price": l["line_extension_amount"]
                if float(l["quantity"]) == 0
                else str((Decimal(l["line_extension_amount"]) / Decimal(str(l["quantity"])))
                         .quantize(Decimal("0.0001"))),
            }
            for l in cn.credited_items
        ],
        "tax_subtotals": _tax_subtotals(cn.credited_items),
        "tax_total": str(cn.tax_total),
        "line_extension_amount": str(cn.line_extension_amount),
        "tax_exclusive_amount": str(cn.tax_exclusive_amount),
        "tax_inclusive_amount": str(cn.tax_inclusive_amount),
        "payable_amount": str(cn.payable_amount),
    })
    return _env.get_template("creditnote_ubl.xml").render(**ctx).encode("utf-8")

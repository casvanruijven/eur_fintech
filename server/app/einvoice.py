"""eInvoice mapper + structured (JSON) exporter — where ZZPay's conceptual
innovation becomes code.

A point-of-sale basket (merchant + line items) is mapped into a fully-computed,
EN 16931 / UBL-inspired :class:`~app.models.Receipt`. Refunds are mapped into a
linked :class:`~app.models.CreditNote`. The same structured object then drives
every export (JSON here, EN 16931 UBL in :mod:`app.ubl`, PDF/PNG in :mod:`app.pdf`).

VAT/total convention (documented on purpose): we round **per line first, then
sum**. This guarantees the line amounts shown on the receipt reconcile exactly to
the document totals — no off-by-a-cent between what the customer sees and the
machine-readable totals.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.models import (
    BasketLine,
    Channel,
    CreditNote,
    Receipt,
    ReceiptStatus,
    _utcnow,
)

CENTS = Decimal("0.01")


def q(amount: Decimal) -> Decimal:
    """Quantise to 2 decimals, banker-free (ROUND_HALF_UP, like a cash register)."""
    return Decimal(amount).quantize(CENTS, rounding=ROUND_HALF_UP)


# --------------------------------------------------------------------------- #
# Line + total computation
# --------------------------------------------------------------------------- #
def _compute_line(idx: int, description: str, quantity: float,
                  unit_price: Decimal, vat_rate: Decimal) -> dict:
    """Compute one structured line.

    ``unit_price`` is the **VAT-inclusive** consumer price as printed at a Dutch
    till (e.g. €6.00 incl. 21% BTW). We back out the net and VAT so the structured
    document carries the net line amount (UBL BT-131) while the receipt still shows
    the familiar gross price. ``gross = net + tax`` holds exactly per line, so the
    line amounts reconcile to the document totals to the cent.
    """
    qty = Decimal(str(quantity))
    unit_gross = Decimal(unit_price)
    rate = Decimal(vat_rate)
    gross = q(qty * unit_gross)               # line total incl. VAT
    net = q(gross / (Decimal(1) + rate))      # BT-131 line net amount
    tax = q(gross - net)                       # line VAT (so net + tax == gross)
    return {
        "id": idx,
        "description": description,
        "quantity": float(quantity),
        "unit_price": str(unit_gross),         # gross unit price (as shown to buyer)
        "vat_rate": str(rate),
        "line_extension_amount": str(net),     # net (excl. VAT)
        "line_tax_total": str(tax),
    }


def _compute_totals(lines: list[dict]) -> dict:
    """Sum the (already-rounded) line amounts into LegalMonetaryTotal/TaxTotal."""
    line_ext = q(sum(Decimal(l["line_extension_amount"]) for l in lines))
    tax_total = q(sum(Decimal(l["line_tax_total"]) for l in lines))
    tax_incl = q(line_ext + tax_total)
    return {
        "line_extension_amount": line_ext,
        "tax_exclusive_amount": line_ext,
        "tax_inclusive_amount": tax_incl,
        "payable_amount": tax_incl,
        "tax_total": tax_total,
    }


# --------------------------------------------------------------------------- #
# Mappers: basket -> Receipt, Receipt -> CreditNote
# --------------------------------------------------------------------------- #
def basket_to_receipt(
    merchant: dict,
    basket: list[BasketLine],
    channel: Channel,
    invoice_id: str,
) -> Receipt:
    """Map a (simulated) POS basket into an unsaved structured Receipt."""
    now = _utcnow()
    lines = [
        _compute_line(i, line.description, line.quantity, line.unit_price, line.vat_rate)
        for i, line in enumerate(basket, start=1)
    ]
    totals = _compute_totals(lines)
    return Receipt(
        invoice_id=invoice_id,
        issue_date=now.date().isoformat(),
        issue_time=now.strftime("%H:%M:%S"),
        currency="EUR",
        channel=channel.value,
        supplier_name=merchant["name"],
        supplier_vat=merchant.get("vat"),
        supplier_address=merchant["address"],
        supplier_country=merchant.get("country", "NL"),
        invoice_lines=lines,
        delivery_url=f"/receipt/{invoice_id}",
        status=ReceiptStatus.GENERATED.value,
        **totals,
    )


def credit_from_receipt(
    receipt: Receipt,
    credit_note_id: str,
    *,
    full: bool = False,
    line_ids: list[int] | None = None,
    reason: str = "Customer returned unused item",
) -> CreditNote:
    """Build a linked CreditNote for the chosen line(s). Original receipt untouched."""
    line_ids = line_ids or []
    if full:
        credited = list(receipt.invoice_lines)
    else:
        wanted = set(line_ids)
        credited = [l for l in receipt.invoice_lines if l["id"] in wanted]
    if not credited:
        raise ValueError("No matching lines to credit")

    totals = _compute_totals(credited)
    now = _utcnow()
    return CreditNote(
        credit_note_id=credit_note_id,
        original_receipt_id=receipt.invoice_id,
        user_id=receipt.user_id,
        issue_date=now.date().isoformat(),
        issue_time=now.strftime("%H:%M:%S"),
        currency=receipt.currency,
        credited_items=credited,
        reason=reason,
        **totals,
    )


# --------------------------------------------------------------------------- #
# Structured JSON export (UBL-flavored keys)
# --------------------------------------------------------------------------- #
def _party(name: str, vat: str | None, address: str, country: str) -> dict:
    party: dict = {"Name": name, "PostalAddress": {"StreetName": address,
                                                   "Country": {"IdentificationCode": country}}}
    if vat:
        party["PartyTaxScheme"] = {"CompanyID": vat, "TaxScheme": {"ID": "VAT"}}
    return party


def _lines_json(lines: list[dict], key: str) -> list[dict]:
    return [
        {
            "ID": l["id"],
            "Quantity": l["quantity"],
            "Description": l["description"],
            "VATRate": l["vat_rate"],
            "LineExtensionAmount": l["line_extension_amount"],
            "TaxAmount": l["line_tax_total"],
        }
        for l in lines
    ]


def receipt_to_einvoice_dict(receipt: Receipt) -> dict:
    """Structured representation of the receipt (the 'machine-readable' view).

    This is the readable JSON twin of the EN 16931 UBL document; it uses the same
    UBL-derived concepts but stays compact for inspection / generic ingestion.
    """
    return {
        "DocumentType": "Invoice",
        "CustomizationID": "urn:cen.eu:en16931:2017",
        "InvoiceID": receipt.invoice_id,
        "IssueDate": receipt.issue_date,
        "IssueTime": receipt.issue_time,
        "DocumentCurrencyCode": receipt.currency,
        "AccountingSupplierParty": _party(
            receipt.supplier_name, receipt.supplier_vat,
            receipt.supplier_address, receipt.supplier_country,
        ),
        "AccountingCustomerParty": {"Name": receipt.buyer_name,
                                    "Email": receipt.buyer_email},
        "InvoiceLine": _lines_json(receipt.invoice_lines, "InvoiceLine"),
        "TaxTotal": {"TaxAmount": str(receipt.tax_total)},
        "LegalMonetaryTotal": {
            "LineExtensionAmount": str(receipt.line_extension_amount),
            "TaxExclusiveAmount": str(receipt.tax_exclusive_amount),
            "TaxInclusiveAmount": str(receipt.tax_inclusive_amount),
            "PayableAmount": str(receipt.payable_amount),
        },
        "ZZPayMeta": {
            "channel": receipt.channel,
            "status": receipt.status,
            "deliveryUrl": receipt.delivery_url,
            "creditNoteId": receipt.credit_note_id,
        },
    }


def credit_note_to_einvoice_dict(cn: CreditNote) -> dict:
    return {
        "DocumentType": "CreditNote",
        "CustomizationID": "urn:cen.eu:en16931:2017",
        "CreditNoteID": cn.credit_note_id,
        "IssueDate": cn.issue_date,
        "IssueTime": cn.issue_time,
        "DocumentCurrencyCode": cn.currency,
        # UBL BillingReference: this credit note corrects the original receipt.
        "BillingReference": {"InvoiceDocumentReference": {"ID": cn.original_receipt_id}},
        "CreditNoteLine": _lines_json(cn.credited_items, "CreditNoteLine"),
        "TaxTotal": {"TaxAmount": str(cn.tax_total)},
        "LegalMonetaryTotal": {
            "LineExtensionAmount": str(cn.line_extension_amount),
            "TaxExclusiveAmount": str(cn.tax_exclusive_amount),
            "TaxInclusiveAmount": str(cn.tax_inclusive_amount),
            "PayableAmount": str(cn.payable_amount),
        },
        "Reason": cn.reason,
        "ZZPayMeta": {"status": cn.status},
    }

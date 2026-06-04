# The eInvoice standard in ZZPay

## What "eInvoice" means

An **electronic invoice (eInvoice)** is not a PDF or a scan — it is a *machine-readable* invoice in a
structured data format that software can process automatically. A PDF must be read (or OCR'd) by a
human; an eInvoice is parsed directly into bookkeeping software with no retyping and no OCR errors.

This is exactly ZZPay's thesis: capture the data **structured at the source**, so the receipt is
already machine-readable the moment it's created.

## PDF vs machine-readable

| | PDF / PNG | eInvoice (UBL) |
|---|---|---|
| Audience | a human | software |
| Ingestion | manual / OCR | direct import |
| Errors | OCR misreads | none (typed fields) |
| In ZZPay | `pdf.py` (public) | `ubl.py` (account-gated) |

ZZPay produces **both** from the same structured `Receipt`: the PDF for people, the UBL for machines.

## EN 16931

**EN 16931** is the European standard that defines the *semantic data model* of a core electronic
invoice — the set of business terms (BT-…) every compliant invoice must carry and the calculation
rules (BR-…) they must satisfy. It is the legal backbone of EU eInvoicing.

ZZPay targets **EN 16931 core**: `CustomizationID = urn:cen.eu:en16931:2017`, `InvoiceTypeCode 380`
(`381` semantics for credit notes). We emit every mandatory term — specification id, invoice number,
issue date, currency, seller (name + VAT + country), buyer (name + country), the VAT breakdown
(`TaxSubtotal` per rate), the document totals (`LegalMonetaryTotal`), and per-line detail
(`InvoiceLine`). Every calculation rule reconciles: line nets sum to the total net, tax = taxable ×
rate, and net + VAT = gross. Because the receipt is already paid at the till, we set
`PrepaidAmount = gross` and `PayableAmount = 0.00`, which also avoids the "payment terms required when
an amount is due" rule.

**Compliance gate.** EN 16931 requires the seller to be identifiable (BR-CO-26). A receipt without a
seller VAT number therefore cannot become a valid e-invoice — `ubl.py` raises `UblComplianceError`
and the API returns **HTTP 422** with a clear message, rather than emitting an invalid document.

Source: <https://www.nen.nl/en/nen-en-16931-1-2026-en-350185>

## UBL 2.1

**UBL (Universal Business Language) 2.1** is the OASIS XML syntax that EN 16931 is bound to. It
defines the `<Invoice>` and `<CreditNote>` document types and the `cbc:`/`cac:` element vocabulary
(`cbc:ID`, `cac:AccountingSupplierParty`, `cac:TaxTotal`, `cac:LegalMonetaryTotal`, `cac:InvoiceLine`,
…). ZZPay renders these in the correct UBL element order in
[`templates/invoice_ubl.xml`](../server/app/templates/invoice_ubl.xml) and
[`templates/creditnote_ubl.xml`](../server/app/templates/creditnote_ubl.xml).

Source: <https://docs.oasis-open.org/ubl/UBL-2.1.html>

## Peppol BIS Billing 3.0

**Peppol BIS Billing 3.0** is the practical specification for *exchanging* EN 16931 invoices and
credit notes over the Peppol network. It is relevant here because it natively supports **both**
invoices and credit notes — which is exactly how ZZPay models refunds.

ZZPay is **not** a certified Peppol Access Point. The Peppol BIS profile additionally mandates
electronic-address endpoints (seller BT-34, buyer BT-49) and a `ProfileID` (BT-23) — these require
Peppol participant IDs we don't have for arbitrary merchants, so they are **deferred** to the Peppol
step. The MVP produces a standards-shaped document that already imports into bookkeeping software; the
Access Point and auto-send are the documented next milestone.

Source: <https://docs.peppol.eu/poacc/billing/3.0/>

## MVP limitations (explicit)

- EN 16931 **core**, not validated by a certified Access Point.
- Single VAT rate per demo basket (grouping handles multi-rate, but it isn't exercised).
- Country defaults to `NL`; real postal addresses and buyer VAT/KVK are simplified.
- Credit notes use `CreditNoteTypeCode 381` with a `BillingReference` to the original — modeled on
  the same EN 16931 / Peppol credit-note flow.

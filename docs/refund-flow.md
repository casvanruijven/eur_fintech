# Refund / return flow

## Principle: never erase the original

In financial administration a refund must **not** delete or overwrite the original receipt. Both the
original sale and its correction have to remain visible for an auditor, the tax authority, and the
accountant. ZZPay models this the way EN 16931 / UBL and Peppol BIS Billing do: a refund creates a
separate **credit note** that *references* the original document.

## How it works

1. On a receipt, the customer opens **Request a refund / return** ([`RefundPanel.tsx`](../client/src/components/RefundPanel.tsx)).
2. They choose the returned line(s) (e.g. "Kit") or a **full refund**.
3. `POST /api/receipts/{invoice_id}/refund` ([`refunds.py`](../server/app/routers/refunds.py)):
   - builds a linked `CreditNote` (`einvoice.credit_from_receipt`) crediting the chosen lines;
   - sets the original receipt's `status = REFUNDED` and `credit_note_id`, **without touching its
     lines or totals**;
   - returns the credit note, plus a **warning** if the receipt had already been emailed.
4. The original receipt is preserved and now shows its linked credit note.

## Worked example (seeded)

| | Original receipt | Credit note |
|---|---|---|
| ID | `ZZP-2026-0001` | `CN-2026-0001` |
| Merchant | Bouwmaat Rotterdam | (references ZZP-2026-0001) |
| Total | €45.98 | refunded item: **Kit**, −€8.98 |
| Status | `REFUNDED` (unchanged lines) | `GENERATED` |

## Already sent to the accountant?

If the original receipt was already emailed (`status = SENT`), the refund response carries:

> "This receipt was already sent to your accountant. ZZPay created a linked credit note so the
> correction remains auditable."

The credit note can then be emailed to the same accountant
(`POST /api/credit-notes/{id}/email`), so their books are corrected with a proper document rather than
an edit-in-place.

## Exports

- **PDF / PNG** of the credit note — public (anyone).
- **JSON / UBL** (EN 16931 `<CreditNote>` with a `cac:BillingReference` to the original) — account-gated.

## Why this matters

This directly answers the lecturer feedback to "explain how returns/refunds work". Refund-as-credit-
note keeps the audit trail clean, mirrors the real Peppol invoice/credit-note exchange, and means a
correction never silently rewrites history.

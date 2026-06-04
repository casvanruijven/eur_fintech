# Architecture

ZZPay is a **receipt infrastructure layer**. A merchant creates a structured receipt at the source;
the same object is delivered through any channel and consumed by a public browser page that can
export, email, and refund it. The codebase is intentionally flat and small so it reads top-to-bottom.

## Text diagram

```
 Merchant Portal                         (client/src/pages/MerchantCheckout.tsx,
   /merchant · /online-checkout            OnlineCheckout.tsx)
        │
        │  POST /api/checkout {merchant_key, channel}
        ▼
 Receipt Service                          (server/app/routers/checkout.py)
   · MERCHANTS registry (POS simulation, single source of truth)
   · einvoice.basket_to_receipt(): VAT split + totals (round per line, then sum)
        │
        ▼
 eInvoice-compatible Receipt Object       (server/app/models.py: Receipt)
   · invoice_id (ZZP-2026-0001), channel, supplier, invoice_lines, totals, status
   · persisted in PostgreSQL via SQLModel
        │
        │  delivery_url = /receipt/{invoice_id}
        ▼
 NFC URL  /  Online Link                  (NFC tap simulated by a button; online link in webshop)
        │
        ▼
 Public Receipt Page                      (client/src/pages/ReceiptView.tsx — NO login)
   ReceiptDocument + ReceiptActions
        │
        ├── Export                        pdf.py (PDF/PNG, public) ·
        │                                 einvoice.py (JSON) · ubl.py (EN 16931 UBL)  [account]
        ├── Email                         email.py → self / accountant (PDF + UBL)    [account]
        └── Refund                        refunds.py → linked CreditNote (original preserved)
```

## Components

### Merchant portal (`/merchant`, `/online-checkout`)
The "source". Each page shows a demo basket and a single action that POSTs to `/api/checkout`. The
backend mints a human-readable `invoice_id` and returns the structured receipt plus a `delivery_url`.
In production this is the merchant's POS; here it is a small hardcoded registry (`MERCHANTS` in
`routers/checkout.py`), which is also the single source of truth for the seeded demo data.

### Receipt service (`einvoice.py` + `models.py`)
`einvoice.basket_to_receipt()` turns a basket into a fully-computed `Receipt`. VAT-inclusive consumer
prices are split into net + VAT **per line, rounded, then summed**, so the line amounts reconcile to
the document totals exactly. `models.py` holds the three tables (`Receipt`, `CreditNote`, `User`) and
all Pydantic schemas — no Repository/DAO/Domain layers.

### eInvoice-compatible receipt object (`models.Receipt`)
Keyed by `invoice_id` (also the public URL slug). Flat typed columns for supplier/buyer/totals; only
`invoice_lines` is JSON. `user_id` is **nullable** — receipts are created ownerless and link to a
user only when that (logged-in) user exports/emails them.

### Public receipt page (`/receipt/:id`)
The most important screen. `GET /api/receipts/{invoice_id}` is **public** (no auth) and flips status
`GENERATED → VIEWED`. `ReceiptActions` reflects the two-tier access model via the optional-auth
context.

### Export services
- **`pdf.py`** — Jinja2 HTML → xhtml2pdf (PDF) → pypdfium2/PIL (PNG). Pure-Python, public.
- **`einvoice.py`** — structured JSON twin of the UBL (account-gated).
- **`ubl.py`** — EN 16931 core UBL 2.1 invoice + credit note (account-gated; buyer = the user).

### Refund service (`refunds.py`)
`POST /api/receipts/{id}/refund` creates a linked `CreditNote` and marks the receipt `REFUNDED`
without mutating its lines. Credit notes have their own public PDF/PNG and gated JSON/UBL exports.

### Browser preference storage (`lib/storage-service.ts`)
`localStorage` remembers a returning visitor's name / email / preferred format on this device — the
"no account required" convenience. The accountant email lives in the **account** (server-side),
because it drives server-side forwarding.

## Auth model

Auth is **optional and progressive**. `auth.py` exposes `CurrentUser` (strict, 401) for gated
endpoints and `OptionalUser` (lenient, `None`) so public pages can detect a logged-in account without
forcing a login. The JWT lives in the httponly `zzpay_token` cookie, so a returning user is
recognised automatically.

## Data flow summary

1. Merchant POSTs a basket → structured `Receipt` persisted, `delivery_url` returned.
2. Customer opens `delivery_url` (NFC/online) → public page renders immediately.
3. Anonymous: download PDF/PNG, request refund. Account: JSON/UBL export, email, send-to-accountant.
4. Refund → linked `CreditNote`; original receipt preserved + `REFUNDED`.

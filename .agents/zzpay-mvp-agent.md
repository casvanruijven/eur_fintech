# ZZPay MVP agent brief

A focused brief for an agent making changes to ZZPay. Read alongside [`../CLAUDE.md`](../CLAUDE.md)
and [`../AGENTS.md`](../AGENTS.md).

## Mission

Maintain a **narrow, demo-ready** MVP that proves the core value process: merchant creates a
structured receipt → delivered via NFC/online → opened with no login → exported / emailed / refunded.
Optimize for **clarity and a working demo**, not production completeness.

## Hard invariants

- **No-login receipt access**: viewing + PDF/PNG are public. Never gate them.
- **EN 16931 data model**: keep the receipt/credit-note shape and the **core** UBL export
  (`urn:cen.eu:en16931:2017`). A receipt without a seller VAT must 422, not emit an invalid invoice.
- **Refund = linked credit note**: the original receipt is immutable on refund.
- **Account-gated structured export + email**: JSON/UBL/email require `CurrentUser`; the first such
  action links the (nullable) `user_id`.
- **VAT math**: round per line, then sum. Prices in the demo baskets are VAT-**inclusive**.

## When adding or changing a feature

1. Stay within MVP scope. If a request implies a real integration (NFC hardware, POS webhook, Peppol
   Access Point, bookkeeping API), **simulate it** and document the simulation — don't build the real
   integration unless explicitly asked.
2. Touch the smallest set of files. Backend logic goes in the matching `routers/<resource>.py` +
   `models.py`; don't add architectural layers.
3. Keep the frontend pattern: typed calls in `api.ts`, React Query for server state, `useAuth`
   non-blocking, downloads via `lib/download.ts`.
4. **Document as you go**: update `README.md` and the relevant `docs/*.md` in the same change.
5. **Verify**: `cd server && pytest` and `cd client && npm run build` must pass. If the DB schema
   changes, note that the dev DB must be reset (`docker compose down -v && up -d`) since there are no
   migrations.

## Common tasks

- **New export format** → add to `einvoice.py`/`ubl.py`/`pdf.py`, expose a URL in `api.ts`, add a
  button in `ExportButtons.tsx`, keep the public/account-gated split.
- **New channel** → it's just another value of `Channel` + a demo page; the receipt object is unchanged.
- **New demo merchant** → add to `MERCHANTS` in `routers/checkout.py` (single source of truth, also
  used by `seed.py`). Ensure the basket has a seller VAT so UBL export works.

## Anti-goals

Enterprise abstractions, real third-party integrations, mandatory login, mutating receipts on refund,
silently emitting non-compliant UBL, returning `password_hash`, hardcoded secrets.

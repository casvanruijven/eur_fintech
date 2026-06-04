# ZZPay conventions (for coding agents)

Keep the codebase flat and readable. This is an MVP graded on clarity and a working demo.

## Product invariants (the spine — don't break)
- **Public no-login receipts**: `GET /api/receipts/{invoice_id}` and **PDF/PNG** downloads need no auth.
- **Account-gated structured export + email**: **JSON/UBL** export and **email / send-to-accountant**
  require `CurrentUser`; the first such action links the nullable `user_id`.
- **EN 16931 core UBL**: missing seller VAT → `UblComplianceError` → HTTP 422 (never an invalid doc).
- **Refund = linked credit note**: never delete/edit the original receipt.
- **VAT**: round per line, then sum; demo basket prices are VAT-inclusive.

## Backend (FastAPI + SQLModel)
- All app code lives directly under `server/app/` — no deep package trees.
- `models.py` holds the SQLModel tables (`User`, `Receipt`, `CreditNote`) **and** their Pydantic
  schemas. Money uses `Decimal`/`Numeric(10, 2)`; decimals are strings in JSON; timestamps are tz-aware UTC.
- Add endpoints to the matching `routers/<resource>.py` (`checkout`, `receipts`, `refunds`, `users`).
  Use the async session via `Depends(get_session)` (commit happens in the dependency on success).
  Protect account-only endpoints with `CurrentUser`; use `OptionalUser` to detect login without forcing it.
- The eInvoice mapper is `einvoice.py`; the EN 16931 UBL is `ubl.py`; PDF/PNG is `pdf.py`
  (pure-Python, no native libs).

## Frontend (React + Vite + Tailwind)
- One typed function per API call in `src/api.ts`; components never call axios directly.
- Server state via React Query; the `useAuth` context is **non-blocking** (401 ⇒ anonymous, no redirect).
- Downloads go through `src/lib/download.ts` (fetch + blob). Reusable UI in `src/components/`; pages in
  `src/pages/`. Icons: `react-icons/pi` only. Brand color via the `brand` Tailwind token. UI copy in English.

## Security
- Tokens live in the httponly `zzpay_token` cookie; never localStorage. Never serialize `password_hash`.
- Don't add real external integrations (NFC/POS/Peppol/bookkeeping) unless explicitly requested.

## Testing
- Backend smoke tests in `server/tests/` use httpx + in-memory SQLite (no Postgres). Don't assert on
  PDF/PNG bytes (status + content-type only). Run `pytest` before finishing.

## Docs
- Update `README.md` and the relevant `docs/*.md` in the same change as any feature change.

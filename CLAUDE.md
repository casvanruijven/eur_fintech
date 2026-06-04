# CLAUDE.md — ZZPay MVP ("Tap. Done. Booked.")

A **receipt infrastructure** MVP for FinTech Assignment 2. A merchant turns a checkout into a
structured, **EN 16931-compatible** receipt; it's delivered over **NFC or an online link**; the
customer opens it **in a plain browser with no login** and can export, email, or refund it. Refunds
are **linked credit notes**. Keep it **flat, small, and demo-ready** — this is a graded MVP, not an
enterprise app.

Stack: FastAPI + SQLModel + PostgreSQL (async) backend; React 19 + Vite + Tailwind + React Query
frontend. UI copy is **English**; receipt *data* is naturally Dutch (Bouwmaat, Schroeven, BTW).

## Invariants — do not break these

1. **Public, no-login receipts.** `GET /api/receipts/{invoice_id}` and the **PDF/PNG** downloads are
   public. Never gate viewing/PDF/PNG behind auth.
2. **Two-tier access.** Structured export (**JSON/UBL**), **email to self**, and **send to
   accountant** require the optional account (`CurrentUser`). A compliant EN 16931 UBL needs a buyer
   identity — that's the reason for the gate. Anonymous users get PDF/PNG + refund only.
3. **EN 16931 data model.** Receipts/credit notes are EN 16931 / UBL-shaped. UBL is **core**
   (`urn:cen.eu:en16931:2017`); a missing seller VAT must raise `UblComplianceError` → HTTP 422, not
   an invalid document. Keep VAT rounding **per line, then sum** so lines reconcile to totals.
4. **Refund = linked credit note.** Never delete or edit the original receipt on refund. Create a
   `CreditNote` referencing it (UBL `BillingReference`) and set the receipt `REFUNDED`.
5. **`user_id` is nullable.** Receipts are created ownerless at checkout and link to a user only when
   that logged-in user exports/emails them.

## Layout

| | |
|---|---|
| Backend | `server/app/` — `main.py`, `config.py`, `database.py`, `models.py`, `auth.py`, `einvoice.py`, `ubl.py`, `pdf.py`, `email.py`, `seed.py`, `routers/`, `templates/` |
| Frontend | `client/src/` — `api.ts`, `auth.tsx`, `App.tsx`, `components/`, `pages/`, `lib/` |
| Tests | `server/tests/` — pytest + httpx against in-memory SQLite |
| Docs | `docs/` — architecture, assignment-mapping, einvoice-standard, refund-flow, multi-channel, merchant-adoption-and-support, ai-orchestration |

## Conventions

- **Backend is flat.** Three tables (`User`, `Receipt`, `CreditNote`) live in `models.py` with their
  Pydantic schemas. No Repository/DAO/Domain layers.
- **One router per resource** under `routers/` (`checkout`, `receipts`, `refunds`, `users`), mounted
  in `main.py`. Use `Depends(get_session)`; commit happens in the dependency on success.
- **Auth:** Argon2 + JWT in the httponly `zzpay_token` cookie. `CurrentUser` (strict) / `OptionalUser`
  (lenient) from `auth.py`. Config via `ZZPAY_*` env vars; never hardcode secrets.
- **Money:** `Decimal` / `Numeric(10, 2)`; decimals serialized as **strings** in JSON. Timestamps are
  tz-aware UTC. Human-readable IDs: `ZZP-{year}-{NNNN}`, `CN-{year}-{NNNN}`.
- **Rendering is pure-Python** (xhtml2pdf + pypdfium2) — no native libs. Don't reintroduce WeasyPrint.
- **Frontend:** typed calls in `api.ts`; server state via React Query; `useAuth` is **non-blocking**
  (401 ⇒ anonymous, no redirect). Downloads via `lib/download.ts` (fetch+blob). Icons from
  `react-icons/pi`. Reusable UI in `components/`; pages in `pages/`.

## Running

- DB: `docker compose up -d` (Postgres on 5434). Reset schema with `docker compose down -v && up -d`.
- Backend: `cd server && uvicorn app.main:app --reload --port 8000` (creates tables + seeds on start).
- Frontend: `cd client && npm run dev`.
- Tests: `cd server && pytest`.

## Don't

- Don't gate receipt viewing / PDF / PNG behind login.
- Don't make refunds mutate or delete the original receipt.
- Don't downgrade the UBL below EN 16931 core, or emit an invalid e-invoice instead of a 422.
- Don't add real external integrations (NFC hardware, POS, Peppol Access Point, bookkeeping APIs)
  unless explicitly asked — they're documented as deferred.
- Don't return `password_hash` in any response. Don't hardcode secrets.
- When you change a feature, **update the README and the relevant `docs/` file** in the same change.

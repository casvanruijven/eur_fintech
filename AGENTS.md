# AGENTS.md — ZZPay MVP

Instructions for any coding agent (Claude, Codex, Gemini, …) working on this repository. This file
mirrors [`CLAUDE.md`](CLAUDE.md); read that for the full conventions. The short version:

## What this is

ZZPay is a **receipt infrastructure MVP** for FinTech Assignment 2: a merchant creates a structured,
**EN 16931-compatible** receipt at checkout; it's delivered via **NFC or an online link**; the
customer opens it **in a plain browser with no login** and can export / email / refund it. Refunds
are **linked credit notes**. FastAPI + SQLModel + PostgreSQL backend; React 19 + Vite + Tailwind
frontend. Keep it **flat, small, and demo-ready**.

## Invariants (do not break)

1. **Public no-login access** to viewing a receipt and downloading **PDF/PNG**.
2. **Account-gated** structured export (**JSON/UBL**) and **email / send-to-accountant** — a
   compliant EN 16931 e-invoice needs a buyer identity.
3. **EN 16931 core UBL.** Missing seller VAT → `UblComplianceError` → HTTP 422 (never an invalid
   document). VAT rounding is **per line, then sum**.
4. **Refund = linked credit note.** Never delete/edit the original receipt.
5. **`user_id` is nullable** — receipts start ownerless and link on first authenticated action.

## Working rules

- Keep the MVP scope **narrow**; prioritise assignment requirements over new features.
- No real external integrations (NFC hardware, POS, Peppol Access Point, bookkeeping APIs) unless
  explicitly requested — they're documented as deferred next steps.
- Update the **README** and the relevant **`docs/`** file in the same change as any feature change.
- Verify before finishing: `cd server && pytest` (in-memory SQLite) and `cd client && npm run build`.
- Never return `password_hash`; never hardcode secrets (use `ZZPAY_*`).

## Where things live

`server/app/` — `models.py` (tables + schemas), `einvoice.py` (mapper + JSON), `ubl.py` (EN 16931
UBL), `pdf.py` (PDF/PNG), `email.py`, `routers/` (checkout, receipts, refunds, users), `templates/`.
`client/src/` — `api.ts`, `auth.tsx`, `App.tsx`, `pages/`, `components/`, `lib/`. Docs in `docs/`.
Detailed per-agent brief: [`.agents/zzpay-mvp-agent.md`](.agents/zzpay-mvp-agent.md).

# ZZPay MVP — Tap. Done. Booked.

> **No app. No scanning. No OCR.** Structured receipt data at the source.

ZZPay is a digital **receipt infrastructure layer** for self-employed professionals (ZZP'ers).
A merchant turns a checkout into a clean, **EN 16931-compatible** structured receipt with one click.
The receipt is delivered over **NFC** (tap a tile) or an **online link**, and the customer opens it
**in a plain browser — no app, no login**. From there they can download, export a real e-invoice,
email it to their accountant, or request a refund that becomes an **auditable credit note**.

This repository is the **MVP** built for **FinTech Assignment 2**. It is deliberately narrow and
demo-ready: it proves the core value-enhancing process in working code, before any expensive POS or
Peppol integrations.

## Team & how we worked

ZZPay was built by Cas van Ruijven, Martijn van der Pijl and David Kloet. We made it together in
live sessions on one laptop, so all commits are under Cas his account. We made all the design,
architecture and review choices together. You can read more about how we used the AI agents in
[`docs/ai-orchestration.md`](docs/ai-orchestration.md).

---

## 1. Assignment context

The assignment asks for a working MVP of the Assignment 1 business model, demonstrating the main
features, explaining the architecture and deployment, oriented at investors, and documenting which
coding agents were used. ZZPay's pitch and the lecturer feedback shaped the scope:

- **Merchants must support it with a low hurdle** → the merchant flow is a lightweight portal that
  does *not* replace the POS (simulated here).
- **Explain returns/refunds** → refunds are modeled as **linked credit notes** (the original receipt
  is never deleted).
- **Explain multi-channel & network effects** → NFC and online checkout deliver the *same* receipt
  object; see [`docs/multi-channel.md`](docs/multi-channel.md).
- **Mention the eInvoice standard** → structured export is **EN 16931 core** UBL 2.1; see
  [`docs/einvoice-standard.md`](docs/einvoice-standard.md).
- **Costs & support are real risks** → [`docs/merchant-adoption-and-support.md`](docs/merchant-adoption-and-support.md).

## 2. Main features

| Feature | Who | Where |
|---|---|---|
| One-click receipt creation at checkout (NFC + online) | Merchant | [`/merchant`](client/src/pages/MerchantCheckout.tsx), [`/online-checkout`](client/src/pages/OnlineCheckout.tsx) |
| Public receipt page — **no login** | Customer | [`/receipt/:id`](client/src/pages/ReceiptView.tsx) |
| Download **PDF / PNG** | Anyone | [`ExportButtons`](client/src/components/ExportButtons.tsx) |
| Export **JSON + EN 16931 UBL** e-invoice | Account holder | [`ubl.py`](server/app/ubl.py) |
| **Email** to self / **send to accountant** (PDF + UBL) | Account holder | [`email.py`](server/app/email.py) |
| **Refund → linked credit note** | Anyone | [`refunds.py`](server/app/routers/refunds.py) |
| **Delete a receipt** from your account | Owner | [`receipts.py`](server/app/routers/receipts.py) |
| Optional account + business details + browser-local preferences | Customer | [`/account`](client/src/pages/Account.tsx) |

### Two-tier access model (the design spine)

- **Anonymous (no login):** view the receipt, download **PDF/PNG**, request a **refund**. The
  **My receipts** list shows only receipts opened on *this device* (localStorage) — never anyone
  else's.
- **Logged-in account holder:** additionally export **JSON/UBL** (a compliant e-invoice needs a
  *buyer* identity), **email to self**, and **send to accountant**. Receipts **link** to the account
  (on checkout / view / export), so **My receipts** is private and account-scoped.

A few rules that keep the books clean:
- **No duplicate sends** — a receipt or credit note can be emailed only **once per recipient** (a
  second send returns 409).
- **Auto-forwarded credit notes** — refunding while logged in (with an accountant configured)
  **automatically emails the linked credit note** to that accountant (PDF + UBL).
- **Your business identity on the e-invoice** — the account page captures company name, BTW & KVK
  number and address; these become the EN 16931 **buyer party** in the UBL/JSON exports.

## 3. Demo flows

1. **NFC checkout** — `/merchant` → *Generate ZZPay Receipt* → *Simulate customer tap* → the public
   receipt page opens (no login).
2. **Online checkout** — `/online-checkout` → *Place order* → *View your ZZPay receipt* → the same
   public page, delivered through a different channel.
3. **Public receipt** — `/receipt/ZZP-2026-0001` (seeded) → download PDF/PNG; log in to export the
   UBL e-invoice or email your accountant.
4. **Refund** — on a receipt, *Request a refund* → pick a line (e.g. "Kit") → a linked credit note
   `CN-…` is created; the original is preserved and marked `REFUNDED`.

Seeded out of the box: **ZZP-2026-0001** (Bouwmaat, NFC, already refunded via **CN-2026-0001**) and
**ZZP-2026-0002** (Shell, online link). Demo account: `demo@zzpay.nl` / `demo1234`.

## 4. Run it locally

**Prerequisites:** Python 3.12, Node 20+, Docker (for PostgreSQL). PDF/PNG rendering is pure-Python
(xhtml2pdf + pypdfium2) — **no native libraries required**, runs on Windows out of the box.

```bash
# 1) Database (PostgreSQL)
docker compose up -d

# 2) Backend
cd server
python -m venv .venv && source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                   # set ZZPAY_JWT_SECRET (any long random string)
python -m uvicorn app.main:app --reload --port 8000    # tables + demo data created on startup

# 3) Frontend (new terminal)
cd client
npm install
npm run dev                                            # http://localhost:5173
```

Open **http://localhost:5173**. Try the merchant demo, tap-to-open a receipt, then log in with the
demo account to export a UBL e-invoice and "send to accountant" (emails are **mocked** — printed to
the backend console unless you configure real SMTP).

> **Resetting the DB:** the schema is created from SQLModel metadata on startup (`create_all`, no
> migrations). If you change the schema, reset the dev database with `docker compose down -v && docker
> compose up -d`.

**Tests:** `cd server && pytest` — runs against in-memory SQLite, no Docker needed.

## 5. Deployment

- **Config is environment-driven** (`ZZPAY_*`), so one image runs anywhere.
- **Backend:** any container host (Fly.io / Render / a VM). Provide a managed PostgreSQL via
  `ZZPAY_POSTGRES_*`, a strong `ZZPAY_JWT_SECRET`, real `ZZPAY_SMTP_*`, and set
  `ZZPAY_CORS_ORIGINS` to the front-end origin. `/api/health` supports health checks.
- **Frontend:** `npm run build` → static `dist/` on any static host/CDN; point `/api` at the backend.
- **Production hardening (documented, not built):** Alembic migrations, rate limiting, email
  verification, background workers for rendering, and a real Peppol Access Point for auto-send.

## 6. Architecture overview

```
 Merchant Portal (/merchant, /online-checkout)
        │  POST /api/checkout            (the "source" — POS simulation)
        ▼
 Receipt Service  ── einvoice.py maps the basket → structured Receipt (VAT split, totals)
        │                                models.py  (Receipt, CreditNote, User) ── PostgreSQL
        ▼
 eInvoice / UBL object
        │  delivery_url
        ▼
 NFC URL  /  Online Link  →  Public Receipt Page (/receipt/:id, no login)
        │
        ├── Export   pdf.py (PDF/PNG) · einvoice.py (JSON) · ubl.py (EN 16931 UBL)
        ├── Email    email.py → user / accountant (PDF + UBL attachments)
        └── Refund   refunds.py → linked CreditNote (original preserved)
```

Full detail in [`docs/architecture.md`](docs/architecture.md). **Stack:** FastAPI + SQLModel +
PostgreSQL (async) backend; React 19 + Vite + Tailwind + React Query frontend. Deliberately **flat
and small** so the whole system reads top-to-bottom.

## 7. eInvoice standard (EN 16931 / UBL / Peppol)

A PDF is human-readable; bookkeeping software needs *machine-readable* structure. ZZPay exports an
**EN 16931 core** UBL 2.1 invoice (`CustomizationID = urn:cen.eu:en16931:2017`) where the **merchant
is the seller** and the **logged-in ZZP'er is the buyer** — a purchase invoice they can hand to their
accountant. We emit every mandatory business term and reconcile every calculation rule. A receipt
without a seller VAT number is **rejected (422)** rather than producing an invalid e-invoice.
We are *not* a certified Peppol Access Point — that, plus auto-send, is the documented next step.
See [`docs/einvoice-standard.md`](docs/einvoice-standard.md).

## 8. Refunds & credit notes

Refunds **never delete or edit** the original receipt. ZZPay issues a linked **credit note** (UBL
`BillingReference` → the original) so the correction stays auditable. If the receipt was already
emailed to the accountant, ZZPay warns and offers to send the credit note the same way. See
[`docs/refund-flow.md`](docs/refund-flow.md).

## 9. Multi-channel

NFC is **one** delivery channel. The same structured receipt object is delivered through an online
link in the webshop flow, and could be delivered through QR, email, or a POS API — they are all just
channels over the same infrastructure. See [`docs/multi-channel.md`](docs/multi-channel.md).

## 10. Limitations / what is mocked

- **NFC tap** is a button ("Simulate customer tap"); no NFC hardware.
- **POS integration** is simulated by a small merchant registry; no real till webhook.
- **Email** is mocked (logged to console) unless real SMTP is configured.
- **UBL** is EN 16931 *core* and not validated by a certified Peppol Access Point; multi-rate VAT,
  postal addresses, and buyer VAT/KVK are simplified.
- **Schema** is created via `create_all` (no migrations); **no rate limiting / email verification**.
- **Anonymous users** get PDF/PNG only — structured export + email require the optional account.

## 11. AI agent usage

Built primarily with **Claude Code** (planning, full-repo edits, self-verification), with **ChatGPT**
used for assignment interpretation and prompt design; humans made all product decisions. Full
write-up: [`docs/ai-orchestration.md`](docs/ai-orchestration.md). Agent instructions live in
[`CLAUDE.md`](CLAUDE.md), [`AGENTS.md`](AGENTS.md), and [`.agents/zzpay-mvp-agent.md`](.agents/zzpay-mvp-agent.md).

## 12. Repository structure

```
server/app/
  main.py          app + routers + lifespan (init_db + seed)
  config.py        ZZPAY_* settings (Postgres, JWT, SMTP)
  database.py      async engine + get_session
  models.py        Receipt, CreditNote, User (tables + Pydantic schemas)
  auth.py          Argon2 + JWT; CurrentUser / OptionalUser deps
  einvoice.py      basket → Receipt mapper, VAT/totals, JSON export
  ubl.py           EN 16931 core UBL (invoice + credit note)
  pdf.py           structured data → PDF/PNG (pure-Python)
  email.py         mock/SMTP send with PDF + UBL attachments
  seed.py          demo account + ZZP-2026-0001/0002 + CN-2026-0001
  routers/         checkout.py, receipts.py, refunds.py, users.py
  templates/       receipt.html, credit_note.html, invoice_ubl.xml, creditnote_ubl.xml
client/src/
  api.ts           typed API client
  auth.tsx         optional-account context (non-blocking)
  App.tsx          public routes
  lib/             format.ts, download.ts (fetch+blob), storage-service.ts
  pages/           Landing, MerchantCheckout, OnlineCheckout, ReceiptView, MerchantReceipts, Account
  components/       ReceiptDocument, ReceiptActions, ExportButtons, RefundPanel, StatusBadge, …
docs/              architecture, assignment-mapping, einvoice-standard, refund-flow,
                   multi-channel, merchant-adoption-and-support, ai-orchestration
```

## 13. License

Educational project for FinTech Assignment 2. © the ZZPay team. No warranty; not for production use.

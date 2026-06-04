# ZZPay — digitale kassabonnen voor ZZP'ers

> Tap. Klaar. Je bonnetje als schone, gestructureerde data — precies waar je het nodig hebt.

ZZPay turns every in-store transaction into a clean, structured digital receipt for self-employed
professionals (ZZP'ers). The customer taps their phone on an NFC tile next to the till; the receipt
is delivered straight to where it's needed — viewable online, downloadable as **PDF** or **PNG**,
or **emailed** to the user or their accountant. No app to install for customers, no new system for
merchants.

This repository is the **MVP** built for FinTech Assignment 2.

---

## 1. The problem & the pitch

ZZP'ers lose hours every month wrangling paper receipts: faded thermal printouts, photos in a
camera roll, shoeboxes at tax time. Each lost receipt is deductible VAT left on the table.

**ZZPay** removes the paper entirely. A tap delivers a structured receipt — typed fields, line
items, VAT split out — that flows directly into the user's admin. For merchants it's a passive
NFC tile, not a new POS. The wedge is consumer-grade simplicity on top of a data format accountants
and bookkeeping software actually want.

## 2. Main features (MVP)

- **Email + password accounts** — so ZZPay knows who the user is and can route receipts automatically.
- **Receipt list & detail** — every bon as clean, structured data (merchant, date, VAT, line items).
- **Download as PDF or PNG** — a polished, shareable document generated from the structured data.
- **Email delivery** — send a receipt to yourself or to your accountant in one click.
- **Accountant routing** — store an accountant's email once; forward any receipt to them.
- **Seeded demo data** — a demo account with sample receipts so the product is explorable instantly.

## 3. Architecture — how the concept maps to code

```
 Customer taps NFC tile            ┌──────────────── Backend (FastAPI) ────────────────┐
   at the merchant's till          │                                                    │
        │  (MVP: mock/manual        │   routers/receipts.py   POST /api/receipts         │
        │   POST instead of NFC)    │            │            structured transaction in   │
        ▼                           │            ▼                                        │
  Structured transaction  ───────► │      models.py  (User, Receipt)  ── PostgreSQL      │
                                    │            │                                        │
   Browser (React SPA)             │            ├── pdf.py    structured data → PDF/PNG   │
   view · download · email  ◄───── │            └── email.py  receipt → user/accountant  │
                                    └────────────────────────────────────────────────────┘
```

The **conceptual innovation** — "turn a transaction into clean, structured data" — lives in
[`models.py`](server/app/models.py): the `Receipt` is fully typed, with VAT split out and line
items as structured JSON. From that single source of truth:

- [`pdf.py`](server/app/pdf.py) renders a polished document (Jinja2 template → WeasyPrint).
- [`email.py`](server/app/email.py) delivers it to the right inbox.
- [`routers/receipts.py`](server/app/routers/receipts.py) exposes it to the SPA, **ownership-scoped**.

**Stack:** FastAPI + SQLModel + PostgreSQL (async) on the back end; React 19 + Vite + Tailwind +
React Query on the front end. The codebase is deliberately **flat and small** (~10 backend modules)
so the whole system is readable top-to-bottom.

**UX:** the front end is a thin, fast SPA. The auth token is an httponly cookie (not reachable from
JS), React Query keeps the receipt list fresh, and every action (download, email) is a single click
from the receipt detail page.

## 4. Deploy & run (product demo)

**Prerequisites:** Python 3.12, Node 20+, Docker (for PostgreSQL).

```bash
# 1) Database
docker compose up -d

# 2) Backend
cd server
python -m venv .venv && source .venv/bin/activate     # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env                                   # set ZZPAY_JWT_SECRET
python -m uvicorn app.main:app --reload --port 8000    # tables + demo data created on startup

# 3) Frontend (new terminal)
cd client
npm install
npm run dev                                            # http://localhost:5173
```

Open http://localhost:5173 and log in with the seeded demo account (the email + password are printed
in the backend console on first run). Browse receipts → open one → **Download PDF/PNG** or **Email**.

> **WeasyPrint note:** PDF/PNG rendering needs WeasyPrint's native libraries (Pango/Cairo). See the
> [WeasyPrint install docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) for
> your OS. Everything else runs without it.

## 5. Scaling prerequisites & technical risks

- **Real merchant integration:** the MVP accepts receipts via a manual/mock `POST`. Production needs
  a merchant-side path (NFC tile → till/POS webhook → `POST /api/receipts`) and per-merchant auth.
- **Schema management:** the MVP auto-creates tables on startup. At scale, switch to **Alembic**
  migrations for safe, versioned schema changes.
- **Render throughput:** PDF/PNG generation is CPU-bound; move it to a background worker/queue and
  cache rendered artifacts.
- **Email deliverability:** sending financial documents at volume requires a real provider
  (SPF/DKIM/DMARC), bounce handling, and rate limits.
- **Bookkeeping integrations:** Moneybird, e-Boekhouden, Tellow, etc. — out of scope for the MVP.

## 6. Operations & maintenance

- **Config** is environment-driven (`ZZPAY_*`), so the same image runs in any environment.
- **Stateless API** behind a connection-pooled async engine; scale horizontally.
- **Backups/PITR** on PostgreSQL (financial data must be recoverable).
- A `/api/health` endpoint supports container/orchestrator health checks.

## 7. Security risks (operator & users)

Receipts are **financial PII**, so the trust boundary matters:

- **Auth:** Argon2 password hashing; JWT in an **httponly, SameSite=Lax** cookie (`Secure` outside
  dev) so tokens aren't exposed to JavaScript/XSS.
- **Authorization:** every receipt endpoint is **ownership-scoped** server-side — a user can only
  read their own receipts (verified by a test).
- **Known MVP gaps (documented, not hidden):** no rate limiting yet (login is brute-forceable — add
  a limiter in production), no email verification, and `create_all` instead of migrations.
- **Operator risks:** protect the `ZZPAY_JWT_SECRET` and DB credentials; receipts at rest should be
  encrypted and access-logged in production.

## 8. Coding agent & orchestration

Built with **Claude Code** as the sole coding agent. Why it fit this project:

- **Plan-mode first:** the architecture was designed and reviewed in a structured plan before any
  code was written, then deliberately *simplified* for a school MVP that has to be explained on camera.
- **Batched scaffolding:** the agent generated the repo in logical, reviewable batches (config →
  data model → auth → receipts/PDF/email → frontend → docs), each verified before moving on.
- **Self-verification:** the agent ran the backend test suite and a production frontend build as it
  went, catching issues immediately rather than at the end.

See [`CLAUDE.md`](CLAUDE.md) and [`.claude/rules/`](.claude/rules) for the agent's working
instructions, and [`HANDOFF.md`](HANDOFF.md) for the next-steps brief.

---

### Suggested GitHub metadata

**Description:** Digital receipt platform for Dutch ZZP'ers — tap an NFC tile, get a clean structured
bon as PDF/PNG or emailed to your accountant. FastAPI + React MVP.

**Topics:** `fintech` `receipts` `zzp` `fastapi` `react` `typescript` `postgresql` `sqlmodel` `mvp`

# ZZPay — quick rules

Flat, demo-ready receipt-infrastructure MVP. Backend: FastAPI + SQLModel + PostgreSQL under
`server/app/` (no Repository/DAO layers; `models.py` = `User`/`Receipt`/`CreditNote` tables +
schemas). Frontend: React + Vite + Tailwind under `client/src/` (typed calls in `api.ts`, React Query
for server state, `react-icons/pi`).

Invariants: **receipts are public** (view + PDF/PNG, no login); **JSON/UBL export + email** are
account-gated; UBL is **EN 16931 core** (missing seller VAT → 422); **refund = linked credit note**
(never mutate the original); `user_id` is nullable (links on first authed action). VAT is rounded per
line then summed; demo basket prices are VAT-inclusive.

Auth = Argon2 + JWT in the httponly `zzpay_token` cookie (`CurrentUser` strict / `OptionalUser`
lenient). Never serialize `password_hash`. Config via `ZZPAY_*`. Rendering is pure-Python (xhtml2pdf +
pypdfium2) — no native libs. Update README + `docs/` when changing features. See `CLAUDE.md` for full
detail.

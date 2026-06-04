# ZZPay — quick rules

Flat MVP. Backend: FastAPI + SQLModel + PostgreSQL under `server/app/` (no Repository/DAO layers;
`models.py` = tables + schemas). Frontend: React + Vite + Tailwind under `client/src/` (typed calls
in `api.ts`, React Query for server state, `react-icons/pi` for icons).

Auth = Argon2 + JWT in the `zzpay_token` httponly cookie. Receipt endpoints are ownership-scoped.
Never serialize `password_hash`. Config via `ZZPAY_*` env vars. See `CLAUDE.md` for full detail.

# CLAUDE.md — ZZPay

Digital receipt platform for ZZP'ers. FastAPI + SQLModel + PostgreSQL backend, React 19 + Vite +
Tailwind + React Query frontend. Keep it **flat and simple** — this is an MVP, not an enterprise app.

## Layout

| | |
|---|---|
| Backend | `server/app/` — `main.py`, `config.py`, `database.py`, `auth.py`, `models.py`, `pdf.py`, `email.py`, `seed.py`, `routers/` |
| Frontend | `client/src/` — `api.ts`, `auth.tsx`, `App.tsx`, `components/`, `pages/` |
| Tests | `server/tests/` — pytest + httpx against in-memory SQLite |

## Conventions

- **Backend is flat.** Two entities only (`User`, `Receipt`) in `models.py`, which holds both the
  SQLModel tables and the Pydantic request/response schemas. Don't add Repository/DAO/Domain layers.
- **One router per resource** under `routers/`, mounted in `main.py`. Endpoints depend on
  `get_current_user` (from `auth.py`) for protected routes.
- **Ownership is enforced server-side.** Receipt endpoints filter by the authenticated user; never
  trust a client-supplied user id.
- **Auth:** Argon2 hashing + JWT in the `zzpay_token` httponly cookie. Config via `ZZPAY_*` env vars.
- **Schema:** tables are created from SQLModel metadata on startup (`init_db`). No migration tool yet.
- **Frontend:** typed calls live in `api.ts`; server state via React Query; auth state via the
  `useAuth` context. Icons from `react-icons/pi`. UI copy is in Dutch.
- **Naming:** Python `snake_case`; React components `PascalCase`; routes `/kebab-case`.

## Running

- Backend: `cd server && uvicorn app.main:app --reload --port 8000` (needs Postgres via `docker compose up -d`).
- Frontend: `cd client && npm run dev`.
- Tests: `cd server && pytest`.

## Don't

- Don't introduce extra architectural layers, a service mesh, or heavy abstractions.
- Don't hardcode secrets — everything sensitive comes from `ZZPAY_*` env vars.
- Don't return `password_hash` in any API response.

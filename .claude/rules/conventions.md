# ZZPay conventions (for Claude Code)

Keep the codebase flat and readable. This is an MVP graded on clarity.

## Backend (FastAPI + SQLModel)
- All app code lives directly under `server/app/` — no deep package trees.
- `models.py` holds SQLModel tables **and** Pydantic schemas for the two entities (`User`, `Receipt`).
- Add new endpoints as a function in the matching `routers/<resource>.py`; protect with
  `Depends(get_current_user)` and scope queries to that user.
- Use the async session via `Depends(get_session)`. Commit happens in the dependency on success.
- Money fields use `Decimal` (`Numeric(10, 2)`); timestamps are timezone-aware UTC.

## Frontend (React + Vite + Tailwind)
- One typed function per API call in `src/api.ts`; components never call axios directly.
- Server state through React Query; auth/session through the `useAuth` context.
- Reusable UI in `src/components/` (`Button`, `Card`, `Input`, `Spinner`, `Layout`); pages in `src/pages/`.
- Icons: `react-icons/pi` only. Brand color via the `brand` Tailwind token (see `index.css`).

## Security
- Tokens live in the `zzpay_token` httponly cookie; never store them in localStorage.
- Never serialize `password_hash`. Never trust a client-provided user id for authorization.

## Testing
- Backend smoke tests in `server/tests/` use httpx + in-memory SQLite (no Postgres needed).
- Avoid asserting on PDF/PNG endpoints in CI — WeasyPrint needs native libs.

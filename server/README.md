# ZZPay API

FastAPI + SQLModel + PostgreSQL. A flat, easy-to-read backend for the ZZPay receipt MVP.

## Run locally

```bash
# 1. Start Postgres (from the repo root)
docker compose up -d

# 2. Set up the environment
cd server
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit ZZPAY_JWT_SECRET

# 3. Run the API (tables are created and demo data is seeded on startup)
python -m uvicorn app.main:app --reload --port 8000
```

- API docs (Swagger): http://localhost:8000/docs
- Health check: http://localhost:8000/api/health
- A demo account is seeded on first run; the email + password are printed to the console.

## Layout

```
app/
  main.py        FastAPI app; creates tables + seeds demo data on startup
  config.py      Settings from environment (.env), ZZPAY_ prefix
  database.py    Async engine + get_session dependency
  auth.py        Password hashing, JWT, get_current_user
  models.py      SQLModel tables (User, Receipt) + request/response schemas
  pdf.py         Render a receipt to PDF / PNG
  email.py       Email a receipt (logs instead of sending when SMTP is unset)
  seed.py        Demo user + sample receipts
  routers/
    users.py     register / login / logout / me
    receipts.py  list / get / create / pdf / png / email
```

## Tests

```bash
pytest
```

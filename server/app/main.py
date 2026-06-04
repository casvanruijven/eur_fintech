"""ZZPay API entrypoint.

On startup we create any missing tables and seed a demo account, then serve the
users + receipts routers. Run with:  uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import seed
from app.config import settings
from app.database import init_db
from app.routers import checkout, receipts, refunds, users

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()      # create tables from the SQLModel metadata
    await seed.run()     # demo user + sample receipts (idempotent)
    yield


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,  # required so the auth cookie is sent cross-origin in dev
    allow_methods=["*"],
    allow_headers=["*"],
)

# The optional account (login / accountant config). Receipts are public — the
# account only unlocks structured export + emailing.
app.include_router(users.router)
# Merchant checkout (the source), public receipts + exports, and refund credit notes.
app.include_router(checkout.router)
app.include_router(receipts.router)
app.include_router(refunds.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name}

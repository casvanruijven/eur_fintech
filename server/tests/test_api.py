"""Smoke tests for the core flows: registration, login, and receipts CRUD.

The PDF/PNG endpoints now render via pure-Python wheels (xhtml2pdf + pypdfium2)
with no native libraries, but we still keep them out of these smoke tests to keep
the suite fast and focused on the API contract; those are verified manually.
"""

import pytest

pytestmark = pytest.mark.asyncio


async def _register_and_login(client) -> None:
    resp = await client.post(
        "/api/register",
        json={
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Jansen",
            "password": "supersecret",
            "accountant_email": "boekhouder@example.com",
        },
    )
    assert resp.status_code == 201, resp.text

    # OAuth2 form login (username = email).
    resp = await client.post(
        "/api/login",
        data={"username": "alice@example.com", "password": "supersecret"},
    )
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()
    # The cookie is stored on the client for subsequent requests.


async def test_register_login_me(client):
    await _register_and_login(client)

    resp = await client.get("/api/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "alice@example.com"
    assert body["accountant_email"] == "boekhouder@example.com"
    assert "password_hash" not in body


async def test_duplicate_registration_conflicts(client):
    await _register_and_login(client)
    resp = await client.post(
        "/api/register",
        json={
            "email": "alice@example.com",
            "first_name": "Alice",
            "last_name": "Again",
            "password": "supersecret",
        },
    )
    assert resp.status_code == 409


async def test_receipts_require_auth(client):
    resp = await client.get("/api/receipts")
    assert resp.status_code == 401


async def test_create_and_list_receipt(client):
    await _register_and_login(client)

    resp = await client.post(
        "/api/receipts",
        json={
            "merchant_name": "Albert Heijn",
            "purchased_at": "2026-06-01T10:30:00Z",
            "total_amount": "12.50",
            "vat_amount": "1.14",
            "line_items": [{"description": "Koffie", "quantity": 1, "unit_price": "12.50"}],
        },
    )
    assert resp.status_code == 201, resp.text
    receipt_id = resp.json()["id"]

    resp = await client.get("/api/receipts")
    assert resp.status_code == 200
    receipts = resp.json()
    assert len(receipts) == 1
    assert receipts[0]["merchant_name"] == "Albert Heijn"

    resp = await client.get(f"/api/receipts/{receipt_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == receipt_id


async def test_cannot_see_other_users_receipt(client):
    # Alice creates a receipt.
    await _register_and_login(client)
    created = await client.post(
        "/api/receipts",
        json={
            "merchant_name": "Shell",
            "purchased_at": "2026-06-01T10:30:00Z",
            "total_amount": "50.00",
            "vat_amount": "8.68",
        },
    )
    receipt_id = created.json()["id"]
    await client.post("/api/logout")

    # Bob registers + logs in, then tries to read Alice's receipt.
    await client.post(
        "/api/register",
        json={
            "email": "bob@example.com",
            "first_name": "Bob",
            "last_name": "de Vries",
            "password": "supersecret",
        },
    )
    await client.post("/api/login", data={"username": "bob@example.com", "password": "supersecret"})

    resp = await client.get(f"/api/receipts/{receipt_id}")
    assert resp.status_code == 404  # ownership enforced

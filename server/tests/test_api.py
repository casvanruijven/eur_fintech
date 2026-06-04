"""Smoke tests for the ZZPay MVP API.

Runs against in-memory SQLite (see conftest) — no Postgres, no Docker. We assert
the two-tier access model: the public layer (view + PDF) needs no login, while the
structured exports (JSON/UBL) and email require an account. PDF byte contents are
not asserted (only status + content-type), keeping the suite fast and portable.

``asyncio_mode = auto`` (pytest.ini) runs the async tests without a marker; the one
synchronous test (the UBL compliance gate) runs as a plain function.
"""

from decimal import Decimal

import pytest

from app.einvoice import basket_to_receipt
from app.models import BasketLine, Channel, User
from app.ubl import UblComplianceError, render_ubl

BOUWMAAT = {"merchant_key": "bouwmaat", "channel": "NFC"}


async def _register_and_login(client, email="ann@zzp.nl", accountant=None):
    body = {
        "email": email,
        "first_name": "Ann",
        "last_name": "Bakker",
        "password": "supersecret",
    }
    if accountant:
        body["accountant_email"] = accountant
    r = await client.post("/api/register", json=body)
    assert r.status_code == 201, r.text
    # OAuth2 form login (username = email) — sets the zzpay_token cookie on the client.
    r = await client.post("/api/login", data={"username": email, "password": "supersecret"})
    assert r.status_code == 200, r.text


async def _checkout(client, payload=BOUWMAAT) -> dict:
    r = await client.post("/api/checkout", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# Public layer
# --------------------------------------------------------------------------- #
async def test_health(client):
    r = await client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_demo_baskets(client):
    r = await client.get("/api/checkout/demo-baskets")
    assert r.status_code == 200
    data = r.json()
    assert "bouwmaat" in data and "shell" in data
    assert data["bouwmaat"]["preview_total"] == "45.98"


async def test_checkout_creates_structured_receipt(client):
    receipt = await _checkout(client)
    assert receipt["invoice_id"].startswith("ZZP-")
    assert receipt["channel"] == "NFC"
    assert receipt["delivery_url"] == f"/receipt/{receipt['invoice_id']}"
    # VAT-inclusive prices reconcile: 2x6 + 25 + 8.98 = 45.98 gross.
    assert Decimal(str(receipt["payable_amount"])) == Decimal("45.98")
    net = Decimal(str(receipt["line_extension_amount"]))
    tax = Decimal(str(receipt["tax_total"]))
    assert net + tax == Decimal(str(receipt["payable_amount"]))


async def test_public_get_no_auth_and_status_viewed(client):
    receipt = await _checkout(client)
    iid = receipt["invoice_id"]
    # No login: opening the receipt works and flips GENERATED -> VIEWED.
    r = await client.get(f"/api/receipts/{iid}")
    assert r.status_code == 200
    assert r.json()["status"] == "VIEWED"


async def test_pdf_public(client):
    receipt = await _checkout(client)
    r = await client.get(f"/api/receipts/{receipt['invoice_id']}/pdf")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


# --------------------------------------------------------------------------- #
# Account-gated exports
# --------------------------------------------------------------------------- #
async def test_structured_exports_require_login(client):
    receipt = await _checkout(client)
    iid = receipt["invoice_id"]
    assert (await client.get(f"/api/receipts/{iid}/json")).status_code == 401
    assert (await client.get(f"/api/receipts/{iid}/ubl")).status_code == 401
    assert (await client.post(f"/api/receipts/{iid}/email", json={})).status_code == 401


async def test_json_export_logged_in(client):
    receipt = await _checkout(client)
    await _register_and_login(client)
    r = await client.get(f"/api/receipts/{receipt['invoice_id']}/json")
    assert r.status_code == 200
    body = r.json()
    assert body["InvoiceID"] == receipt["invoice_id"]
    assert "LegalMonetaryTotal" in body


async def test_ubl_export_en16931(client):
    receipt = await _checkout(client)
    await _register_and_login(client)
    r = await client.get(f"/api/receipts/{receipt['invoice_id']}/ubl")
    assert r.status_code == 200
    assert "xml" in r.headers["content-type"]
    xml = r.text
    assert "urn:cen.eu:en16931:2017" in xml
    assert f"<cbc:ID>{receipt['invoice_id']}</cbc:ID>" in xml
    assert 'currencyID="EUR"' in xml
    assert "NL123456789B01" in xml          # seller VAT
    assert "Ann Bakker" in xml              # buyer = the logged-in user


def test_ubl_requires_seller_vat():
    """The compliance gate: a receipt without a seller VAT cannot become a valid
    EN 16931 e-invoice -> UblComplianceError (surfaced as 422 by the API)."""
    merchant = {"name": "No VAT Shop", "vat": None, "address": "Rotterdam", "country": "NL"}
    receipt = basket_to_receipt(
        merchant, [BasketLine(description="Item", quantity=1, unit_price="10.00")],
        Channel.NFC, "ZZP-2026-9999",
    )
    buyer = User(email="b@x.nl", first_name="B", last_name="Buyer", password_hash="x")
    with pytest.raises(UblComplianceError):
        render_ubl(receipt, buyer)


# --------------------------------------------------------------------------- #
# Refund -> linked credit note
# --------------------------------------------------------------------------- #
async def test_refund_creates_linked_credit_note(client):
    receipt = await _checkout(client)
    iid = receipt["invoice_id"]
    kit = next(l for l in receipt["invoice_lines"] if l["description"] == "Kit")

    r = await client.post(f"/api/receipts/{iid}/refund", json={"line_ids": [kit["id"]]})
    assert r.status_code == 201, r.text
    cn = r.json()["credit_note"]
    assert cn["credit_note_id"].startswith("CN-")
    assert cn["original_receipt_id"] == iid
    # The refunded line totals the gross "Kit" price (8.98).
    assert Decimal(str(cn["payable_amount"])) == Decimal("8.98")

    # Original receipt is preserved (3 lines) and marked REFUNDED + linked.
    after = (await client.get(f"/api/receipts/{iid}")).json()
    assert after["status"] == "REFUNDED"
    assert after["credit_note_id"] == cn["credit_note_id"]
    assert len(after["invoice_lines"]) == 3

    # Credit note is publicly viewable; a second refund conflicts.
    assert (await client.get(f"/api/credit-notes/{cn['credit_note_id']}")).status_code == 200
    assert (await client.post(f"/api/receipts/{iid}/refund",
                              json={"full": True})).status_code == 409


async def test_credit_note_ubl_has_billing_reference(client):
    receipt = await _checkout(client)
    iid = receipt["invoice_id"]
    await _register_and_login(client)
    r = await client.post(f"/api/receipts/{iid}/refund", json={"full": True})
    cn_id = r.json()["credit_note"]["credit_note_id"]

    r = await client.get(f"/api/credit-notes/{cn_id}/ubl")
    assert r.status_code == 200
    xml = r.text
    assert "<CreditNote" in xml
    assert "BillingReference" in xml
    assert iid in xml  # references the original receipt


# --------------------------------------------------------------------------- #
# Email (mock) — requires login, updates status
# --------------------------------------------------------------------------- #
async def test_email_to_self_marks_sent(client):
    receipt = await _checkout(client)
    iid = receipt["invoice_id"]
    await _register_and_login(client, email="self@zzp.nl")
    r = await client.post(f"/api/receipts/{iid}/email", json={})
    assert r.status_code == 200
    after = (await client.get(f"/api/receipts/{iid}")).json()
    assert after["status"] == "SENT"
    assert after["sent_to_user_email"] == "self@zzp.nl"
    assert after["sent_at"] is not None


async def test_send_to_accountant_requires_config(client):
    receipt = await _checkout(client)
    iid = receipt["invoice_id"]
    # No accountant on file -> 400.
    await _register_and_login(client, email="noacct@zzp.nl")
    assert (await client.post(f"/api/receipts/{iid}/send-to-accountant")).status_code == 400


async def test_send_to_accountant_ok(client):
    receipt = await _checkout(client)
    iid = receipt["invoice_id"]
    await _register_and_login(client, email="hasacct@zzp.nl",
                              accountant="boekhouder@demo-accounting.nl")
    r = await client.post(f"/api/receipts/{iid}/send-to-accountant")
    assert r.status_code == 200, r.text
    after = (await client.get(f"/api/receipts/{iid}")).json()
    assert after["sent_to_accountant_email"] == "boekhouder@demo-accounting.nl"
    assert after["status"] == "SENT"

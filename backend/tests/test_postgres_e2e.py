"""End-to-end API workflow test against an isolated PostgreSQL database."""
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.session import get_engine, get_session_factory
from app.main import app
from app.models.user import User, UserRole


DATABASE_URL = os.getenv("WMS_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(not DATABASE_URL, reason="requires WMS_TEST_DATABASE_URL")


@pytest.fixture()
def api():
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    engine = create_engine(DATABASE_URL)
    tables = "inventory_movements, inventory_adjustments, transfer_order_lines, transfer_orders, import_order_lines, import_orders, export_order_lines, export_orders, inventory, refresh_tokens, products, categories, units, suppliers, warehouses, users"
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE"))

    factory = sessionmaker(bind=engine)
    session = factory()
    admin = User(username="e2e-admin", email="e2e-admin@example.test", password_hash=hash_password("Password1"), role=UserRole.ADMIN)
    session.add(admin)
    session.commit()
    session.close()

    with TestClient(app) as client:
        yield client

    get_engine.cache_clear()
    get_session_factory.cache_clear()
    engine.dispose()


def login(client, identifier, password="Password1"):
    response = client.post("/api/v1/auth/login", json={"identifier": identifier, "password": password})
    assert response.status_code == 200
    return response.json()


def headers(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def create(client, path, token, data):
    response = client.post(path, headers=headers(token), json=data)
    assert response.status_code == 201, response.text
    return response.json()


def test_postgresql_full_inventory_workflow(api):
    staff_registration = api.post("/api/v1/auth/register", json={"username": "e2e-staff", "email": "e2e-staff@example.com", "password": "Password1"})
    assert staff_registration.status_code == 201
    assert staff_registration.json()["role"] == "STAFF"
    assert api.post("/api/v1/auth/register", json={"username": "not-admin", "email": "not-admin@example.com", "password": "Password1", "role": "ADMIN"}).status_code == 422

    staff = login(api, "e2e-staff")
    admin = login(api, "e2e-admin")
    assert api.get("/api/v1/auth/me", headers=headers(staff)).json()["username"] == "e2e-staff"
    rotated = api.post("/api/v1/auth/refresh", json={"refresh_token": staff["refresh_token"]})
    assert rotated.status_code == 200
    assert api.post("/api/v1/auth/refresh", json={"refresh_token": staff["refresh_token"]}).status_code == 401
    # Reusing the rotated token revokes its entire family by design. Start a
    # new family for the remaining authorization and logout checks.
    staff = login(api, "e2e-staff")

    category = create(api, "/api/v1/categories", admin, {"name": "E2E"})
    unit = create(api, "/api/v1/units", admin, {"name": "piece", "code": "PCS"})
    product = create(api, "/api/v1/products", admin, {"sku": "E2E-ITEM", "name": "E2E Item", "category_id": category["id"], "unit_id": unit["id"]})
    assert api.get("/api/v1/products", headers=headers(staff), params={"search": "E2E-ITEM"}).json()[0]["id"] == product["id"]
    assert api.post("/api/v1/products", headers=headers(staff), json={"sku": "DENIED", "name": "Denied", "category_id": category["id"], "unit_id": unit["id"]}).status_code == 403
    warehouse_one = create(api, "/api/v1/warehouses", admin, {"code": "E2E-W1", "name": "E2E source"})
    warehouse_two = create(api, "/api/v1/warehouses", admin, {"code": "E2E-W2", "name": "E2E destination"})
    supplier = create(api, "/api/v1/suppliers", admin, {"code": "E2E-S", "name": "E2E supplier"})
    assert api.get("/api/v1/warehouses", headers=headers(staff), params={"search": "source"}).json()[0]["id"] == warehouse_one["id"]

    imported = create(api, "/api/v1/imports", staff, {"warehouse_id": warehouse_one["id"], "supplier_id": supplier["id"], "lines": [{"product_id": product["id"], "quantity": "30"}]})
    assert api.post(f"/api/v1/imports/{imported['id']}/confirm", headers=headers(staff)).status_code == 200
    assert api.post(f"/api/v1/imports/{imported['id']}/confirm", headers=headers(staff)).status_code == 409

    staff_export = create(api, "/api/v1/exports", staff, {"warehouse_id": warehouse_one["id"], "lines": [{"product_id": product["id"], "quantity": "40"}]})
    assert api.post(f"/api/v1/exports/{staff_export['id']}/confirm", headers=headers(staff)).status_code == 409
    inventory = api.get("/api/v1/inventory", headers=headers(staff), params={"warehouse_id": warehouse_one["id"], "product_id": product["id"]}).json()
    assert inventory[0]["quantity"] == "30.000"

    admin_export = create(api, "/api/v1/exports", admin, {"warehouse_id": warehouse_one["id"], "lines": [{"product_id": product["id"], "quantity": "35"}]})
    assert api.post(f"/api/v1/exports/{admin_export['id']}/confirm", headers=headers(admin)).status_code == 200
    replenishment = create(api, "/api/v1/imports", admin, {"warehouse_id": warehouse_one["id"], "supplier_id": supplier["id"], "lines": [{"product_id": product["id"], "quantity": "10"}]})
    assert api.post(f"/api/v1/imports/{replenishment['id']}/confirm", headers=headers(admin)).status_code == 200

    transfer = create(api, "/api/v1/transfers", staff, {"source_warehouse_id": warehouse_one["id"], "destination_warehouse_id": warehouse_two["id"], "lines": [{"product_id": product["id"], "quantity": "3"}]})
    assert api.post(f"/api/v1/transfers/{transfer['id']}/confirm", headers=headers(staff)).status_code == 200
    excessive_transfer = create(api, "/api/v1/transfers", admin, {"source_warehouse_id": warehouse_one["id"], "destination_warehouse_id": warehouse_two["id"], "lines": [{"product_id": product["id"], "quantity": "99"}]})
    assert api.post(f"/api/v1/transfers/{excessive_transfer['id']}/confirm", headers=headers(admin)).status_code == 409
    assert api.get("/api/v1/transfers", headers=headers(staff), params={"warehouse_id": warehouse_two["id"], "status": "CONFIRMED"}).json()[0]["id"] == transfer["id"]

    assert api.post("/api/v1/adjustments", headers=headers(staff), json={"warehouse_id": warehouse_two["id"], "product_id": product["id"], "quantity_delta": "1", "reason": "count"}).status_code == 403
    adjustment = api.post("/api/v1/adjustments", headers=headers(admin), json={"warehouse_id": warehouse_two["id"], "product_id": product["id"], "quantity_delta": "1", "reason": "count"})
    assert adjustment.status_code == 201
    assert api.post("/api/v1/adjustments", headers=headers(admin), json={"warehouse_id": warehouse_two["id"], "product_id": product["id"], "quantity_delta": "-5", "reason": "invalid"}).status_code == 409

    threshold_url = f"/api/v1/inventory/{warehouse_two['id']}/{product['id']}/threshold"
    assert api.put(threshold_url, headers=headers(admin), json={"min_quantity": "4"}).status_code == 200
    alerts = api.get("/api/v1/alerts/low-stock", headers=headers(staff), params={"warehouse_id": warehouse_two["id"]}).json()
    assert len(alerts) == 1 and alerts[0]["quantity"] == "4.000"
    assert api.put(threshold_url, headers=headers(admin), json={"min_quantity": None}).status_code == 200
    assert api.get("/api/v1/alerts/low-stock", headers=headers(staff), params={"warehouse_id": warehouse_two["id"]}).json() == []

    movements = api.get("/api/v1/inventory-movements", headers=headers(staff), params={"product_id": product["id"], "limit": 100}).json()
    assert sum(item["movement_type"] == "TRANSFER" for item in movements) == 2
    assert sum(item["movement_type"] == "ADJUSTMENT" for item in movements) == 1
    assert api.post("/api/v1/auth/logout", json={"refresh_token": staff["refresh_token"]}).status_code == 204
    assert api.post("/api/v1/auth/refresh", json={"refresh_token": staff["refresh_token"]}).status_code == 401

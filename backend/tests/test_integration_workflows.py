"""End-to-end API workflows using an isolated in-memory database."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_token, hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


@pytest.fixture()
def api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    admin = User(username="admin", email="admin@integration.test", password_hash=hash_password("Password1"), role=UserRole.ADMIN)
    staff = User(username="staff", email="staff@integration.test", password_hash=hash_password("Password1"), role=UserRole.STAFF)
    session.add_all([admin, staff]); session.commit()
    admin_token, _ = create_token(subject=admin.id, token_type="access", expires_delta=timedelta(minutes=5))
    staff_token, _ = create_token(subject=staff.id, token_type="access", expires_delta=timedelta(minutes=5))
    session.close()

    def override_db():
        request_session = factory()
        try:
            yield request_session
        finally:
            request_session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as client:
        yield client, {"Authorization": f"Bearer {admin_token}"}, {"Authorization": f"Bearer {staff_token}"}
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def bootstrap(api):
    client, admin, _ = api
    category = client.post("/api/v1/categories", headers=admin, json={"name": "integration"}).json()["id"]
    unit = client.post("/api/v1/units", headers=admin, json={"name": "piece", "code": "PCS"}).json()["id"]
    product = client.post("/api/v1/products", headers=admin, json={"sku": "INT-1", "name": "Integration Product", "category_id": category, "unit_id": unit}).json()["id"]
    source = client.post("/api/v1/warehouses", headers=admin, json={"code": "INT-SRC", "name": "Source"}).json()["id"]
    destination = client.post("/api/v1/warehouses", headers=admin, json={"code": "INT-DST", "name": "Destination"}).json()["id"]
    supplier = client.post("/api/v1/suppliers", headers=admin, json={"code": "INT-SUP", "name": "Supplier"}).json()["id"]
    return source, destination, supplier, product


def quantity(client, headers, warehouse_id, product_id):
    response = client.get("/api/v1/inventory", headers=headers, params={"warehouse_id": warehouse_id, "product_id": product_id})
    records = response.json()
    return records[0]["quantity"] if records else None


def test_full_inventory_lifecycle_and_movement_consistency(api):
    client, admin, staff = api
    source, destination, supplier, product = bootstrap(api)
    imported = client.post("/api/v1/imports", headers=staff, json={"warehouse_id": source, "supplier_id": supplier, "lines": [{"product_id": product, "quantity": "10"}]})
    assert imported.status_code == 201
    import_id = imported.json()["id"]
    assert client.post(f"/api/v1/imports/{import_id}/confirm", headers=staff).status_code == 200
    assert quantity(client, staff, source, product) == "10.000"
    assert client.post(f"/api/v1/imports/{import_id}/confirm", headers=staff).status_code == 409
    assert quantity(client, staff, source, product) == "10.000"

    transfer = client.post("/api/v1/transfers", headers=staff, json={"source_warehouse_id": source, "destination_warehouse_id": destination, "lines": [{"product_id": product, "quantity": "4"}]}).json()["id"]
    assert client.post(f"/api/v1/transfers/{transfer}/confirm", headers=staff).status_code == 200
    assert quantity(client, admin, source, product) == "6.000"
    assert quantity(client, admin, destination, product) == "4.000"

    assert client.put(f"/api/v1/inventory/{destination}/{product}/threshold", headers=admin, json={"min_quantity": "4"}).status_code == 200
    alerts = client.get("/api/v1/alerts/low-stock", headers=staff).json()
    assert [(row["warehouse_id"], row["product_id"]) for row in alerts] == [(destination, product)]
    assert client.post("/api/v1/adjustments", headers=staff, json={"warehouse_id": destination, "product_id": product, "quantity_delta": "1", "reason": "Denied"}).status_code == 403
    assert client.post("/api/v1/adjustments", headers=admin, json={"warehouse_id": destination, "product_id": product, "quantity_delta": "-5", "reason": "Cannot go negative"}).status_code == 409
    assert quantity(client, admin, destination, product) == "4.000"


def test_export_permissions_and_failed_operation_rollback(api):
    client, admin, staff = api
    source, _, supplier, product = bootstrap(api)
    import_id = client.post("/api/v1/imports", headers=admin, json={"warehouse_id": source, "supplier_id": supplier, "lines": [{"product_id": product, "quantity": "2"}]}).json()["id"]
    client.post(f"/api/v1/imports/{import_id}/confirm", headers=admin)
    export_id = client.post("/api/v1/exports", headers=staff, json={"warehouse_id": source, "lines": [{"product_id": product, "quantity": "3"}]}).json()["id"]
    assert client.post(f"/api/v1/exports/{export_id}/confirm", headers=staff).status_code == 409
    assert quantity(client, admin, source, product) == "2.000"
    assert client.get(f"/api/v1/exports/{export_id}", headers=staff).json()["status"] == "DRAFT"
    assert client.post(f"/api/v1/exports/{export_id}/cancel", headers=staff).status_code == 204
    assert client.post(f"/api/v1/exports/{export_id}/confirm", headers=staff).status_code == 409
    admin_export = client.post("/api/v1/exports", headers=admin, json={"warehouse_id": source, "lines": [{"product_id": product, "quantity": "3"}]}).json()["id"]
    assert client.post(f"/api/v1/exports/{admin_export}/confirm", headers=admin).status_code == 200
    assert quantity(client, admin, source, product) == "-1.000"

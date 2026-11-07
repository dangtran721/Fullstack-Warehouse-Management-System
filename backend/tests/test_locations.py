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
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    session = factory()
    admin = User(username="admin", email="admin@example.com", password_hash=hash_password("Password1"), role=UserRole.ADMIN)
    staff = User(username="staff", email="staff@example.com", password_hash=hash_password("Password1"), role=UserRole.STAFF)
    session.add_all([admin, staff]); session.commit()
    admin_token, _ = create_token(subject=admin.id, token_type="access", expires_delta=timedelta(minutes=5))
    staff_token, _ = create_token(subject=staff.id, token_type="access", expires_delta=timedelta(minutes=5))
    session.close()

    def override_db():
        request_session = factory()
        try: yield request_session
        finally: request_session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client, {"Authorization": f"Bearer {admin_token}"}, {"Authorization": f"Bearer {staff_token}"}
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_warehouse_crud_validation_filter_and_authorization(client):
    payload = {"code": " wh-main ", "name": "Main Warehouse", "address": "1 Storage Road"}
    created = client[0].post("/api/v1/warehouses", headers=client[1], json=payload)
    assert created.status_code == 201 and created.json()["code"] == "WH-MAIN"
    warehouse_id = created.json()["id"]
    assert client[0].post("/api/v1/warehouses", headers=client[1], json=payload).status_code == 409
    assert client[0].post("/api/v1/warehouses", headers=client[1], json={"code": "", "name": ""}).status_code == 422
    assert client[0].post("/api/v1/warehouses", headers=client[2], json={"code": "STAFF", "name": "Denied"}).status_code == 403
    assert client[0].get("/api/v1/warehouses", headers=client[2], params={"search": "main", "is_active": True, "limit": 1}).status_code == 200
    updated = client[0].put(f"/api/v1/warehouses/{warehouse_id}", headers=client[1], json={"is_active": False})
    assert updated.status_code == 200 and not updated.json()["is_active"]
    assert len(client[0].get("/api/v1/warehouses", headers=client[1], params={"is_active": False}).json()) == 1
    assert client[0].get("/api/v1/warehouses/00000000-0000-0000-0000-000000000000", headers=client[1]).status_code == 404
    assert client[0].delete(f"/api/v1/warehouses/{warehouse_id}", headers=client[1]).status_code == 204


def test_supplier_crud_validation_filter_and_authorization(client):
    payload = {"code": " sup-01 ", "name": "Acme Supplies", "email": "BUYER@ACME.EXAMPLE", "phone": "+84 912 345 678"}
    created = client[0].post("/api/v1/suppliers", headers=client[1], json=payload)
    assert created.status_code == 201 and created.json()["code"] == "SUP-01" and created.json()["email"] == "buyer@acme.example"
    supplier_id = created.json()["id"]
    assert client[0].post("/api/v1/suppliers", headers=client[1], json=payload).status_code == 409
    assert client[0].post("/api/v1/suppliers", headers=client[1], json={"code": "INVALID", "name": "Invalid", "email": "bad", "phone": "abc"}).status_code == 422
    assert client[0].post("/api/v1/suppliers", headers=client[2], json={"code": "STAFF", "name": "Denied"}).status_code == 403
    assert client[0].get("/api/v1/suppliers", headers=client[2], params={"search": "acme", "limit": 1}).status_code == 200
    updated = client[0].put(f"/api/v1/suppliers/{supplier_id}", headers=client[1], json={"name": "Acme Updated", "is_active": False})
    assert updated.status_code == 200 and updated.json()["name"] == "Acme Updated" and not updated.json()["is_active"]
    assert len(client[0].get("/api/v1/suppliers", headers=client[1], params={"is_active": False}).json()) == 1
    assert client[0].delete(f"/api/v1/suppliers/{supplier_id}", headers=client[1]).status_code == 204
    assert client[0].get(f"/api/v1/suppliers/{supplier_id}", headers=client[1]).status_code == 404

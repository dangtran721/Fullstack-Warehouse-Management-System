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
        try:
            yield request_session
        finally:
            request_session.close()

    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client, {"Authorization": f"Bearer {admin_token}"}, {"Authorization": f"Bearer {staff_token}"}
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def category(client, name="food"):
    return client[0].post("/api/v1/categories", headers=client[1], json={"name": name})


def unit(client, name="piece", code="PCS"):
    return client[0].post("/api/v1/units", headers=client[1], json={"name": name, "code": code})


def product_payload(category_id, unit_id, sku="SKU-1", name="Rice", is_active=True):
    return {"sku": sku, "name": name, "category_id": category_id, "unit_id": unit_id, "is_active": is_active}


def test_category_crud_validation_authorization_and_references(client):
    created = category(client, "  Food  ")
    assert created.status_code == 201 and created.json()["name"] == "food"
    category_id = created.json()["id"]
    assert category(client, "FOOD").status_code == 409
    assert category(client, "   ").status_code == 422
    assert client[0].post("/api/v1/categories", headers=client[2], json={"name": "staff"}).status_code == 403
    assert client[0].get("/api/v1/categories", headers=client[2]).status_code == 200
    assert client[0].put(f"/api/v1/categories/{category_id}", headers=client[1], json={"name": "grocery"}).status_code == 200
    assert client[0].get("/api/v1/categories/00000000-0000-0000-0000-000000000000", headers=client[1]).status_code == 404
    created_unit = unit(client).json()
    assert client[0].post("/api/v1/products", headers=client[1], json=product_payload(category_id, created_unit["id"])).status_code == 201
    assert client[0].delete(f"/api/v1/categories/{category_id}", headers=client[1]).status_code == 409


def test_unit_crud_validation_authorization_and_references(client):
    created = unit(client, "  box ", " bx ")
    assert created.status_code == 201 and created.json()["code"] == "BX"
    unit_id = created.json()["id"]
    assert unit(client, "other", "BX").status_code == 409
    assert unit(client, "box", "OTHER").status_code == 409
    assert unit(client, "", "X").status_code == 422
    assert client[0].post("/api/v1/units", headers=client[2], json={"name": "staff", "code": "S"}).status_code == 403
    assert client[0].get("/api/v1/units", headers=client[2]).status_code == 200
    assert client[0].put(f"/api/v1/units/{unit_id}", headers=client[1], json={"name": "carton", "code": "CTN"}).status_code == 200
    category_id = category(client).json()["id"]
    assert client[0].post("/api/v1/products", headers=client[1], json=product_payload(category_id, unit_id)).status_code == 201
    assert client[0].delete(f"/api/v1/units/{unit_id}", headers=client[1]).status_code == 409


def test_product_crud_filters_search_pagination_and_authorization(client):
    category_id = category(client).json()["id"]
    second_category_id = category(client, "drink").json()["id"]
    unit_id = unit(client).json()["id"]
    first = client[0].post("/api/v1/products", headers=client[1], json=product_payload(category_id, unit_id, " rice-1 ", "Premium Rice"))
    assert first.status_code == 201 and first.json()["sku"] == "RICE-1"
    product_id = first.json()["id"]
    assert client[0].post("/api/v1/products", headers=client[1], json=product_payload(category_id, unit_id, "RICE-1", "Other")).status_code == 409
    assert client[0].post("/api/v1/products", headers=client[1], json=product_payload("00000000-0000-0000-0000-000000000000", unit_id)).status_code == 404
    assert client[0].post("/api/v1/products", headers=client[1], json=product_payload(category_id, "00000000-0000-0000-0000-000000000000")).status_code == 404
    assert client[0].post("/api/v1/products", headers=client[2], json=product_payload(category_id, unit_id, "STAFF-1")).status_code == 403
    assert client[0].post("/api/v1/products", headers=client[1], json=product_payload(second_category_id, unit_id, "WATER-1", "Water", False)).status_code == 201
    updated = client[0].put(f"/api/v1/products/{product_id}", headers=client[1], json={"name": "White Rice", "is_active": False})
    assert updated.status_code == 200 and updated.json()["name"] == "White Rice" and not updated.json()["is_active"]
    assert len(client[0].get("/api/v1/products", headers=client[2], params={"search": "rice", "skip": 0, "limit": 1}).json()) == 1
    assert len(client[0].get("/api/v1/products", headers=client[1], params={"category_id": second_category_id, "is_active": False}).json()) == 1
    assert client[0].get(f"/api/v1/products/{product_id}", headers=client[2]).status_code == 200
    assert client[0].put(f"/api/v1/products/{product_id}", headers=client[2], json={"name": "Denied"}).status_code == 403
    assert client[0].delete(f"/api/v1/products/{product_id}", headers=client[1]).status_code == 204
    assert client[0].get(f"/api/v1/products/{product_id}", headers=client[1]).status_code == 404

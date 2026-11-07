from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import require_roles
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
    def override_db():
        session = factory()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_db
    with TestClient(app) as test_client:
        yield test_client, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def register(client, username="user", email="user@example.com", password="Password1"):
    return client[0].post("/api/v1/auth/register", json={"username": username, "email": email, "password": password})


def login(client, identifier="user", password="Password1"):
    return client[0].post("/api/v1/auth/login", json={"identifier": identifier, "password": password})


def test_registration_validation_and_hashing(client):
    response = register(client)
    assert response.status_code == 201
    assert "password_hash" not in response.json()
    assert register(client).status_code == 409
    assert register(client, "other", "USER@example.com").status_code == 409
    assert register(client, "bad", "invalid", "Password1").status_code == 422
    assert register(client, "weak", "weak@example.com", "password").status_code == 422
    assert client[0].post("/api/v1/auth/register", json={"username":"admin", "email":"a@b.com", "password":"Password1", "role":"ADMIN"}).status_code == 422
    user = client[1]().query(User).filter_by(username="user").one()
    assert user.password_hash != "Password1" and user.password_hash.startswith("$argon2id$")


def test_login_me_rotation_logout_and_reuse(client):
    register(client)
    tokens = login(client).json()
    assert tokens["token_type"] == "bearer"
    assert client[0].get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).status_code == 200
    rotated = client[0].post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).json()
    assert client[0].post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
    assert client[0].post("/api/v1/auth/refresh", json={"refresh_token": rotated["refresh_token"]}).status_code == 401
    tokens = login(client).json()
    assert client[0].post("/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}).status_code == 204
    assert client[0].post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_invalid_credentials_token_types_expiry_and_roles(client):
    assert login(client).status_code == 401
    register(client)
    tokens = login(client).json()
    assert login(client, password="Wrongpass1").status_code == 401
    assert client[0].post("/api/v1/auth/refresh", json={"refresh_token": tokens["access_token"]}).status_code == 401
    assert client[0].get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['refresh_token']}"}).status_code == 401
    session = client[1]()
    user = session.query(User).one()
    expired, _ = create_token(subject=user.id, token_type="access", expires_delta=timedelta(seconds=-1))
    assert client[0].get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    expired_refresh, _ = create_token(subject=user.id, token_type="refresh", expires_delta=timedelta(seconds=-1))
    assert client[0].post("/api/v1/auth/refresh", json={"refresh_token": expired_refresh}).status_code == 401
    user.is_active = False; session.commit()
    assert login(client).status_code == 401
    assert client[0].get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}).status_code == 401
    admin = User(username="admin", email="admin@example.com", password_hash=hash_password("Password1"), role=UserRole.ADMIN)
    session.add(admin); session.commit()
    assert require_roles(UserRole.ADMIN)(admin) == admin
    with pytest.raises(Exception) as error:
        require_roles(UserRole.ADMIN)(user)
    assert error.value.status_code == 403

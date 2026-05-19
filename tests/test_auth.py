import pytest
from httpx import AsyncClient
from app.core.security import hash_password
from app.models.user import User


class TestAuth:
    async def test_login_success(self, client: AsyncClient, db_session):
        # Create a user first
        user = User(
            username="testuser",
            password_hash=hash_password("test123"),
            nickname="Test User",
        )
        db_session.add(user)
        await db_session.commit()

        resp = await client.post("/api/v1/auth/login", json={
            "username": "testuser",
            "password": "test123",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    async def test_login_wrong_password(self, client: AsyncClient, db_session):
        user = User(
            username="testuser2",
            password_hash=hash_password("test123"),
        )
        db_session.add(user)
        await db_session.commit()

        resp = await client.post("/api/v1/auth/login", json={
            "username": "testuser2",
            "password": "wrong",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 401

    async def test_get_me(self, client: AsyncClient, db_session):
        user = User(
            username="meuser",
            password_hash=hash_password("test123"),
            nickname="Me User",
        )
        db_session.add(user)
        await db_session.commit()

        # Login to get token
        resp = await client.post("/api/v1/auth/login", json={
            "username": "meuser",
            "password": "test123",
        })
        token = resp.json()["data"]["access_token"]

        # Get me
        resp = await client.get("/api/v1/auth/me", headers={
            "Authorization": f"Bearer {token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["username"] == "meuser"

    async def test_unauthorized_no_token(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 422  # Missing required header

    async def test_change_password(self, client: AsyncClient, db_session):
        user = User(
            username="pwduser",
            password_hash=hash_password("oldpass"),
        )
        db_session.add(user)
        await db_session.commit()

        resp = await client.post("/api/v1/auth/login", json={
            "username": "pwduser",
            "password": "oldpass",
        })
        token = resp.json()["data"]["access_token"]

        resp = await client.put("/api/v1/auth/me/password", json={
            "old_password": "oldpass",
            "new_password": "newpass123",
        }, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200

    async def test_refresh_token(self, client: AsyncClient, db_session):
        user = User(
            username="refreshuser",
            password_hash=hash_password("test123"),
        )
        db_session.add(user)
        await db_session.commit()

        resp = await client.post("/api/v1/auth/login", json={
            "username": "refreshuser",
            "password": "test123",
        })
        refresh = resp.json()["data"]["refresh_token"]

        resp = await client.post("/api/v1/auth/refresh", json={
            "refresh_token": refresh,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data["data"]

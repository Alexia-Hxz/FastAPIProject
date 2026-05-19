import pytest
from httpx import AsyncClient
from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role, UserRole


class TestUserManagement:
    @pytest.fixture
    async def admin_user(self, db_session):
        user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            is_superuser=True,
        )
        db_session.add(user)
        await db_session.commit()
        return user

    @pytest.fixture
    async def admin_token(self, client, admin_user):
        resp = await client.post("/api/v1/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })
        return resp.json()["data"]["access_token"]

    async def test_list_users(self, client: AsyncClient, admin_token, db_session):
        for i in range(15):
            db_session.add(User(
                username=f"user{i}",
                password_hash=hash_password("pass"),
                nickname=f"User {i}",
            ))
        await db_session.commit()

        resp = await client.get("/api/v1/users", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 200
        assert data["data"]["pagination"]["total"] >= 15

    async def test_create_user(self, client: AsyncClient, admin_token):
        resp = await client.post("/api/v1/users", json={
            "username": "newuser",
            "password": "newpassword123",
            "nickname": "New User",
            "email": "new@test.com",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "newuser"

    async def test_create_duplicate_user(self, client: AsyncClient, admin_token, db_session):
        db_session.add(User(username="dup", password_hash=hash_password("pass")))
        await db_session.commit()

        resp = await client.post("/api/v1/users", json={
            "username": "dup",
            "password": "dup123456",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.json()["code"] == 400

    async def test_get_user(self, client: AsyncClient, admin_token, db_session):
        user = User(username="getuser", password_hash=hash_password("pass"))
        db_session.add(user)
        await db_session.commit()

        resp = await client.get(f"/api/v1/users/{user.id}", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert resp.status_code == 200
        assert resp.json()["data"]["username"] == "getuser"

    async def test_update_user(self, client: AsyncClient, admin_token, db_session):
        user = User(username="upduser", password_hash=hash_password("pass"))
        db_session.add(user)
        await db_session.commit()

        resp = await client.put(f"/api/v1/users/{user.id}", json={
            "nickname": "Updated Name",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["nickname"] == "Updated Name"

    async def test_delete_user(self, client: AsyncClient, admin_token, db_session):
        user = User(username="deluser", password_hash=hash_password("pass"))
        db_session.add(user)
        await db_session.commit()

        resp = await client.delete(f"/api/v1/users/{user.id}", headers={
            "Authorization": f"Bearer {admin_token}",
        })
        assert resp.status_code == 200

    async def test_permission_denied(self, client: AsyncClient, db_session):
        # Non-admin, non-superuser without proper roles
        user = User(username="normal", password_hash=hash_password("pass"))
        db_session.add(user)
        await db_session.commit()

        resp = await client.post("/api/v1/auth/login", json={
            "username": "normal", "password": "pass",
        })
        token = resp.json()["data"]["access_token"]

        resp = await client.get("/api/v1/users", headers={
            "Authorization": f"Bearer {token}",
        })
        # Should be forbidden (no user:list permission)
        assert resp.json()["code"] in [403, 401]

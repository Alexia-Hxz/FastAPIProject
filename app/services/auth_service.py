import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.models.user import User
from app.schemas.auth import TokenResponse


class AuthService:
    @staticmethod
    async def login(db: AsyncSession, username: str, password: str) -> TokenResponse:
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Incorrect username or password")
        if not user.is_active:
            raise ValueError("Account is disabled")

        user.last_login_at = datetime.now(timezone.utc)
        await db.flush()

        access_token = create_access_token(str(user.id))
        refresh_token = create_refresh_token(str(user.id))
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)

    @staticmethod
    async def get_current_user(db: AsyncSession, token: str) -> User:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("Invalid token type")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Invalid token")
        user_id = uuid.UUID(user_id_str)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")
        if not user.is_active:
            raise ValueError("Account is disabled")
        return user

    @staticmethod
    async def refresh_token(db: AsyncSession, refresh_token_str: str) -> TokenResponse:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        user_id_str = payload.get("sub")
        if not user_id_str:
            raise ValueError("Invalid token")

        user_id = uuid.UUID(user_id_str)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("User not found or inactive")

        access_token = create_access_token(str(user.id))
        new_refresh_token = create_refresh_token(str(user.id))
        return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)

    @staticmethod
    async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str) -> None:
        if not verify_password(old_password, user.password_hash):
            raise ValueError("Old password is incorrect")
        user.password_hash = hash_password(new_password)
        await db.flush()

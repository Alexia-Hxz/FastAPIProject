from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.exceptions import UnauthorizedError, ForbiddenError, BadRequestError
from app.models.user import User
from app.services.auth_service import AuthService
import uuid


def parse_uuid(value: str, field_name: str = "id") -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError:
        raise BadRequestError(f"Invalid {field_name} format")


async def get_token_from_header(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise UnauthorizedError("Invalid authorization header")
    token = authorization[7:]
    if not token:
        raise UnauthorizedError("Token is empty")
    return token


async def get_current_user(
    request: Request,
    token: str = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    # Check token blacklist (skip if Redis unavailable)
    if redis is not None:
        is_blacklisted = await redis.get(f"blacklist:{token}")
        if is_blacklisted:
            raise UnauthorizedError("Token has been revoked")

    try:
        user = await AuthService.get_current_user(db, token)
        request.state.current_user_id = str(user.id)
        request.state.current_username = user.username
        return user
    except ValueError as e:
        raise UnauthorizedError(str(e))


def require_permission(permission_code: str):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.is_superuser:
            return current_user
        user_perms = set()
        for role in current_user.roles:
            if role.is_active:
                for menu in role.menus:
                    if menu.permission_code:
                        user_perms.add(menu.permission_code)
        if permission_code not in user_perms:
            raise ForbiddenError(f"Missing permission: {permission_code}")
        return current_user

    return checker

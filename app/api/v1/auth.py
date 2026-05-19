from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.redis import get_redis
from app.dependencies import get_current_user, get_token_from_header
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshTokenRequest,
    ChangePasswordRequest,
    UserProfileUpdate,
    UserInfoResponse,
)
from app.schemas.common import ResponseModel
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=ResponseModel[TokenResponse])
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        token = await AuthService.login(db, request.username, request.password)
        return ResponseModel(data=token)
    except ValueError as e:
        return ResponseModel(code=401, message=str(e), data=None)


@router.post("/logout", response_model=ResponseModel)
async def logout(
    token: str = Depends(get_token_from_header),
    current_user: User = Depends(get_current_user),
    redis=Depends(get_redis),
):
    if redis is not None:
        await redis.setex(f"blacklist:{token}", 1800, "1")
    return ResponseModel(message="Logged out successfully")


@router.post("/refresh", response_model=ResponseModel[TokenResponse])
async def refresh_token(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        token = await AuthService.refresh_token(db, request.refresh_token)
        return ResponseModel(data=token)
    except ValueError as e:
        return ResponseModel(code=401, message=str(e), data=None)


@router.get("/me", response_model=ResponseModel[UserInfoResponse])
async def get_me(current_user: User = Depends(get_current_user)):
    return ResponseModel(data=UserInfoResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        last_login_at=str(current_user.last_login_at) if current_user.last_login_at else None,
        created_at=str(current_user.created_at),
    ))


@router.put("/me", response_model=ResponseModel[UserInfoResponse])
async def update_me(
    data: "UserProfileUpdate",
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(current_user, field, value)
    await db.flush()
    return ResponseModel(data=UserInfoResponse(
        id=str(current_user.id),
        username=current_user.username,
        email=current_user.email,
        phone=current_user.phone,
        nickname=current_user.nickname,
        avatar_url=current_user.avatar_url,
        is_active=current_user.is_active,
        is_superuser=current_user.is_superuser,
        last_login_at=str(current_user.last_login_at) if current_user.last_login_at else None,
        created_at=str(current_user.created_at),
    ))


@router.put("/me/password", response_model=ResponseModel)
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    token: str = Depends(get_token_from_header),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
):
    try:
        await AuthService.change_password(db, current_user, request.old_password, request.new_password)
        # Invalidate current token so old password can't be used
        if redis is not None:
            await redis.setex(f"blacklist:{token}", 1800, "1")
        return ResponseModel(message="Password changed successfully")
    except ValueError as e:
        return ResponseModel(code=400, message=str(e), data=None)

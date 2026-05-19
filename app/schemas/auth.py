from pydantic import BaseModel, Field
from app.schemas.common import ORMBase


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class UserProfileUpdate(BaseModel):
    email: str | None = None
    phone: str | None = None
    nickname: str | None = None


class UserInfoResponse(ORMBase):
    id: str
    username: str
    email: str | None
    phone: str | None
    nickname: str | None
    avatar_url: str | None
    is_active: bool
    is_superuser: bool
    last_login_at: str | None
    created_at: str

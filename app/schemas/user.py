from pydantic import BaseModel, Field
from app.schemas.common import ORMBase


class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)
    email: str | None = None
    phone: str | None = None
    nickname: str | None = None
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    email: str | None = None
    phone: str | None = None
    nickname: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserResponse(ORMBase):
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


class UserRoleAssign(BaseModel):
    role_ids: list[str]

from pydantic import BaseModel, Field
from app.schemas.common import ORMBase


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None


class RoleResponse(ORMBase):
    id: str
    name: str
    code: str
    description: str | None
    is_active: bool
    created_at: str


class RoleMenuAssign(BaseModel):
    menu_ids: list[str]

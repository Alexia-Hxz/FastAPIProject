from pydantic import BaseModel, Field
from app.schemas.common import ORMBase


class MenuCreate(BaseModel):
    parent_id: str | None = None
    name: str = Field(..., min_length=1, max_length=50)
    menu_type: str = "menu"
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    permission_code: str | None = None
    sort_order: int = 0
    is_visible: bool = True


class MenuUpdate(BaseModel):
    parent_id: str | None = None
    name: str | None = None
    menu_type: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    permission_code: str | None = None
    sort_order: int | None = None
    is_visible: bool | None = None


class MenuResponse(ORMBase):
    id: str
    parent_id: str | None
    name: str
    menu_type: str
    path: str | None
    component: str | None
    icon: str | None
    permission_code: str | None
    sort_order: int
    is_visible: bool
    children: list["MenuResponse"] | None = None

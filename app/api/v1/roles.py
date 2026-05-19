from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, parse_uuid
from app.models.user import User
from app.schemas.common import ResponseModel, PageResponse, PageInfo
from app.schemas.role import RoleCreate, RoleUpdate, RoleResponse, RoleMenuAssign
from app.services.role_service import RoleService

router = APIRouter(prefix="/roles", tags=["角色管理"])


@router.get("", response_model=ResponseModel[PageResponse[RoleResponse]])
async def list_roles(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:list")),
):
    roles, total = await RoleService.get_list(db, page, page_size)
    items = [RoleResponse.model_validate(r) for r in roles]
    return ResponseModel(data=PageResponse(items=items, pagination=PageInfo(page=page, page_size=page_size, total=total)))


@router.get("/all", response_model=ResponseModel[list[RoleResponse]])
async def get_all_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roles = await RoleService.get_all(db)
    return ResponseModel(data=[RoleResponse.model_validate(r) for r in roles])


@router.post("", response_model=ResponseModel[RoleResponse])
async def create_role(
    data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:create")),
):
    try:
        role = await RoleService.create(db, data)
        return ResponseModel(data=RoleResponse.model_validate(role))
    except ValueError as e:
        return ResponseModel(code=400, message=str(e), data=None)


@router.get("/{role_id}", response_model=ResponseModel[RoleResponse])
async def get_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:read")),
):
    role = await RoleService.get_by_id(db, parse_uuid(role_id))
    if not role:
        return ResponseModel(code=404, message="Role not found", data=None)
    return ResponseModel(data=RoleResponse.model_validate(role))


@router.put("/{role_id}", response_model=ResponseModel[RoleResponse])
async def update_role(
    role_id: str,
    data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:update")),
):
    role = await RoleService.get_by_id(db, parse_uuid(role_id))
    if not role:
        return ResponseModel(code=404, message="Role not found", data=None)
    updated = await RoleService.update(db, role, data)
    return ResponseModel(data=RoleResponse.model_validate(updated))


@router.delete("/{role_id}", response_model=ResponseModel)
async def delete_role(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:delete")),
):
    role = await RoleService.get_by_id(db, parse_uuid(role_id))
    if not role:
        return ResponseModel(code=404, message="Role not found", data=None)
    await RoleService.delete(db, role)
    return ResponseModel(message="Role deleted")


@router.put("/{role_id}/menus", response_model=ResponseModel)
async def assign_role_menus(
    role_id: str,
    data: RoleMenuAssign,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:assign")),
):
    role = await RoleService.get_by_id(db, parse_uuid(role_id))
    if not role:
        return ResponseModel(code=404, message="Role not found", data=None)
    await RoleService.assign_menus(db, role, data.menu_ids)
    return ResponseModel(message="Menus assigned")


@router.get("/{role_id}/menus", response_model=ResponseModel[list[str]])
async def get_role_menus(
    role_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("role:assign")),
):
    role = await RoleService.get_by_id(db, parse_uuid(role_id))
    if not role:
        return ResponseModel(code=404, message="Role not found", data=None)
    menu_ids = await RoleService.get_menu_ids(db, role)
    return ResponseModel(data=menu_ids)

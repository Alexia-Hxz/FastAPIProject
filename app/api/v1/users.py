from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, parse_uuid
from app.models.user import User
from app.schemas.common import ResponseModel, PageResponse, PageInfo, PaginationParams
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserRoleAssign
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=ResponseModel[PageResponse[UserResponse]])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:list")),
):
    users, total = await UserService.get_list(db, page, page_size, keyword)
    items = [UserResponse.model_validate(u) for u in users]
    return ResponseModel(data=PageResponse(items=items, pagination=PageInfo(page=page, page_size=page_size, total=total)))


@router.post("", response_model=ResponseModel[UserResponse])
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:create")),
):
    try:
        user = await UserService.create(db, data)
        return ResponseModel(data=UserResponse.model_validate(user))
    except ValueError as e:
        return ResponseModel(code=400, message=str(e), data=None)


@router.get("/{user_id}", response_model=ResponseModel[UserResponse])
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:read")),
):
    user = await UserService.get_by_id(db, parse_uuid(user_id))
    if not user:
        return ResponseModel(code=404, message="User not found", data=None)
    return ResponseModel(data=UserResponse.model_validate(user))


@router.put("/{user_id}", response_model=ResponseModel[UserResponse])
async def update_user(
    user_id: str,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:update")),
):
    user = await UserService.get_by_id(db, parse_uuid(user_id))
    if not user:
        return ResponseModel(code=404, message="User not found", data=None)
    updated = await UserService.update(db, user, data)
    return ResponseModel(data=UserResponse.model_validate(updated))


@router.delete("/{user_id}", response_model=ResponseModel)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:delete")),
):
    user = await UserService.get_by_id(db, parse_uuid(user_id))
    if not user:
        return ResponseModel(code=404, message="User not found", data=None)
    await UserService.delete(db, user)
    return ResponseModel(message="User deleted")


@router.put("/{user_id}/roles", response_model=ResponseModel)
async def assign_user_roles(
    user_id: str,
    data: UserRoleAssign,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("user:assign")),
):
    user = await UserService.get_by_id(db, parse_uuid(user_id))
    if not user:
        return ResponseModel(code=404, message="User not found", data=None)
    await UserService.assign_roles(db, user, data.role_ids)
    return ResponseModel(message="Roles assigned")

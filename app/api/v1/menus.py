from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, parse_uuid
from app.models.user import User
from app.schemas.common import ResponseModel
from app.schemas.menu import MenuCreate, MenuUpdate, MenuResponse
from app.services.menu_service import MenuService

router = APIRouter(prefix="/menus", tags=["菜单管理"])


@router.get("/tree", response_model=ResponseModel[list[MenuResponse]])
async def menu_tree(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("menu:list")),
):
    tree = await MenuService.get_tree(db)
    return ResponseModel(data=tree)


@router.get("/user", response_model=ResponseModel[list[MenuResponse]])
async def user_menus(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.is_superuser:
        tree = await MenuService.get_tree(db)
    else:
        tree = await MenuService.get_user_menus(db, current_user.id)
    return ResponseModel(data=tree)


@router.post("", response_model=ResponseModel[MenuResponse])
async def create_menu(
    data: MenuCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("menu:create")),
):
    menu = await MenuService.create(db, data)
    return ResponseModel(data=MenuResponse.model_validate(menu))


@router.put("/{menu_id}", response_model=ResponseModel[MenuResponse])
async def update_menu(
    menu_id: str,
    data: MenuUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("menu:update")),
):
    menu = await MenuService.get_by_id(db, parse_uuid(menu_id))
    if not menu:
        return ResponseModel(code=404, message="Menu not found", data=None)
    updated = await MenuService.update(db, menu, data)
    return ResponseModel(data=MenuResponse.model_validate(updated))


@router.delete("/{menu_id}", response_model=ResponseModel)
async def delete_menu(
    menu_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("menu:delete")),
):
    menu = await MenuService.get_by_id(db, parse_uuid(menu_id))
    if not menu:
        return ResponseModel(code=404, message="Menu not found", data=None)
    await MenuService.delete(db, menu)
    return ResponseModel(message="Menu deleted")

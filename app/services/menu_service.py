import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.menu import Menu, RoleMenu
from app.schemas.menu import MenuCreate, MenuUpdate, MenuResponse


class MenuService:
    @staticmethod
    async def get_tree(db: AsyncSession) -> list[MenuResponse]:
        result = await db.execute(select(Menu).order_by(Menu.sort_order))
        menus = result.scalars().all()
        return MenuService._build_tree(menus)

    @staticmethod
    def _build_tree(menus: list[Menu], parent_id: uuid.UUID | None = None) -> list[MenuResponse]:
        tree = []
        for menu in menus:
            if menu.parent_id == parent_id:
                resp = MenuResponse(
                    id=str(menu.id),
                    parent_id=str(menu.parent_id) if menu.parent_id else None,
                    name=menu.name,
                    menu_type=menu.menu_type,
                    path=menu.path,
                    component=menu.component,
                    icon=menu.icon,
                    permission_code=menu.permission_code,
                    sort_order=menu.sort_order,
                    is_visible=menu.is_visible,
                    children=MenuService._build_tree(menus, menu.id),
                )
                tree.append(resp)
        return tree

    @staticmethod
    async def get_user_menus(db: AsyncSession, user_id: uuid.UUID) -> list[MenuResponse]:
        from app.models.user import User
        from app.models.role import Role, UserRole

        result = await db.execute(
            select(Menu)
            .join(RoleMenu, RoleMenu.menu_id == Menu.id)
            .join(Role, Role.id == RoleMenu.role_id)
            .join(UserRole, UserRole.role_id == Role.id)
            .join(User, User.id == UserRole.user_id)
            .where(User.id == user_id)
            .where(Role.is_active == True)
            .where(Menu.is_visible == True)
            .order_by(Menu.sort_order)
        )
        assigned = result.unique().scalars().all()
        if not assigned:
            return []

        menu_ids = {m.id for m in assigned}
        parent_ids = {m.parent_id for m in assigned if m.parent_id} - menu_ids
        while parent_ids:
            r = await db.execute(select(Menu).where(Menu.id.in_(parent_ids)))
            parents = list(r.scalars().all())
            menu_ids |= {p.id for p in parents}
            parent_ids = {p.parent_id for p in parents if p.parent_id} - menu_ids

        result = await db.execute(
            select(Menu).where(Menu.id.in_(menu_ids)).order_by(Menu.sort_order)
        )
        return MenuService._build_tree(result.scalars().all())

    @staticmethod
    async def get_by_id(db: AsyncSession, menu_id: uuid.UUID) -> Menu | None:
        result = await db.execute(select(Menu).where(Menu.id == menu_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: MenuCreate) -> Menu:
        parent_id = uuid.UUID(data.parent_id) if data.parent_id else None
        menu = Menu(
            parent_id=parent_id,
            name=data.name,
            menu_type=data.menu_type,
            path=data.path,
            component=data.component,
            icon=data.icon,
            permission_code=data.permission_code,
            sort_order=data.sort_order,
            is_visible=data.is_visible,
        )
        db.add(menu)
        await db.flush()
        return menu

    @staticmethod
    async def update(db: AsyncSession, menu: Menu, data: MenuUpdate) -> Menu:
        update_data = data.model_dump(exclude_unset=True)
        if "parent_id" in update_data:
            update_data["parent_id"] = uuid.UUID(update_data["parent_id"]) if update_data["parent_id"] else None
        for field, value in update_data.items():
            setattr(menu, field, value)
        await db.flush()
        return menu

    @staticmethod
    async def delete(db: AsyncSession, menu: Menu) -> None:
        # Move children to parent
        result = await db.execute(select(Menu).where(Menu.parent_id == menu.id))
        for child in result.scalars().all():
            child.parent_id = menu.parent_id
        await db.delete(menu)
        await db.flush()

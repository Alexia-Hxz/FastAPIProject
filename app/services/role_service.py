import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.role import Role, UserRole
from app.models.menu import RoleMenu
from app.schemas.role import RoleCreate, RoleUpdate


class RoleService:
    @staticmethod
    async def get_list(db: AsyncSession, page: int = 1, page_size: int = 10):
        query = select(Role)
        count_query = select(func.count(Role.id))
        total = (await db.execute(count_query)).scalar()
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(Role.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all(), total

    @staticmethod
    async def get_all(db: AsyncSession):
        result = await db.execute(select(Role).where(Role.is_active == True))
        return result.scalars().all()

    @staticmethod
    async def get_by_id(db: AsyncSession, role_id: uuid.UUID) -> Role | None:
        result = await db.execute(select(Role).where(Role.id == role_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: RoleCreate) -> Role:
        result = await db.execute(select(Role).where(Role.code == data.code))
        if result.scalar_one_or_none():
            raise ValueError(f"Role code '{data.code}' already exists")
        role = Role(name=data.name, code=data.code, description=data.description)
        db.add(role)
        await db.flush()
        return role

    @staticmethod
    async def update(db: AsyncSession, role: Role, data: RoleUpdate) -> Role:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(role, field, value)
        await db.flush()
        return role

    @staticmethod
    async def delete(db: AsyncSession, role: Role) -> None:
        # Remove associations first
        ur_result = await db.execute(select(UserRole).where(UserRole.role_id == role.id))
        for ur in ur_result.scalars().all():
            await db.delete(ur)
        rm_result = await db.execute(select(RoleMenu).where(RoleMenu.role_id == role.id))
        for rm in rm_result.scalars().all():
            await db.delete(rm)
        await db.delete(role)
        await db.flush()

    @staticmethod
    async def get_menu_ids(db: AsyncSession, role: Role) -> list[str]:
        result = await db.execute(
            select(RoleMenu.menu_id).where(RoleMenu.role_id == role.id)
        )
        return [str(mid) for (mid,) in result.all()]

    @staticmethod
    async def assign_menus(db: AsyncSession, role: Role, menu_ids: list[str]) -> None:
        result = await db.execute(select(RoleMenu).where(RoleMenu.role_id == role.id))
        for rm in result.scalars().all():
            await db.delete(rm)
        await db.flush()
        seen = set()
        for mid in menu_ids:
            if mid in seen:
                continue
            seen.add(mid)
            try:
                db.add(RoleMenu(role_id=role.id, menu_id=uuid.UUID(mid)))
            except ValueError:
                pass
        await db.flush()

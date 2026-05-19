import uuid
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role, UserRole
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    @staticmethod
    async def get_list(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 10,
        keyword: str | None = None,
    ):
        query = select(User)
        count_query = select(func.count(User.id))

        if keyword:
            filter_cond = or_(
                User.username.contains(keyword),
                User.nickname.contains(keyword),
                User.email.contains(keyword),
            )
            query = query.where(filter_cond)
            count_query = count_query.where(filter_cond)

        total = (await db.execute(count_query)).scalar()
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(User.created_at.desc())
        result = await db.execute(query)
        users = result.scalars().all()

        return users, total

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def create(db: AsyncSession, data: UserCreate) -> User:
        # Check uniqueness
        result = await db.execute(select(User).where(User.username == data.username))
        if result.scalar_one_or_none():
            raise ValueError(f"Username '{data.username}' already exists")

        user = User(
            username=data.username,
            password_hash=hash_password(data.password),
            email=data.email,
            phone=data.phone,
            nickname=data.nickname,
            is_active=data.is_active,
            is_superuser=data.is_superuser,
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def update(db: AsyncSession, user: User, data: UserUpdate) -> User:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await db.flush()
        return user

    @staticmethod
    async def delete(db: AsyncSession, user: User) -> None:
        user.is_active = False
        await db.flush()

    @staticmethod
    async def assign_roles(db: AsyncSession, user: User, role_ids: list[str]) -> None:
        # Remove existing roles
        result = await db.execute(select(UserRole).where(UserRole.user_id == user.id))
        for er in result.scalars().all():
            await db.delete(er)

        # Assign new roles
        for rid in role_ids:
            db.add(UserRole(user_id=user.id, role_id=uuid.UUID(rid)))
        await db.flush()

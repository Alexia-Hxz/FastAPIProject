import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func, and_, update, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.operation_log import OperationLog


class LogService:
    @staticmethod
    async def get_list(
        db: AsyncSession,
        page: int = 1,
        page_size: int = 10,
        username: str | None = None,
        module: str | None = None,
        method: str | None = None,
        status_code: int | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        exclude_method: str | None = None,
        include_deleted: bool = False,
    ):
        conditions = [OperationLog.is_deleted == include_deleted]
        if username:
            conditions.append(OperationLog.username == username)
        if module:
            conditions.append(OperationLog.module == module)
        if method:
            conditions.append(OperationLog.request_method == method.upper())
        if status_code is not None:
            conditions.append(OperationLog.response_status == status_code)
        if exclude_method:
            conditions.append(OperationLog.request_method != exclude_method.upper())
        if start_time:
            conditions.append(OperationLog.created_at >= datetime.fromisoformat(start_time))
        if end_time:
            conditions.append(OperationLog.created_at <= datetime.fromisoformat(end_time))

        query = select(OperationLog)
        count_query = select(func.count(OperationLog.id))
        query = query.where(and_(*conditions))
        count_query = count_query.where(and_(*conditions))

        total = (await db.execute(count_query)).scalar()
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(OperationLog.created_at.desc())
        result = await db.execute(query)
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, log_id: uuid.UUID) -> OperationLog | None:
        result = await db.execute(select(OperationLog).where(OperationLog.id == log_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def soft_delete(db: AsyncSession, log_id: uuid.UUID, deleted_by: str) -> bool:
        result = await db.execute(
            update(OperationLog)
            .where(OperationLog.id == log_id, OperationLog.is_deleted == False)
            .values(is_deleted=True, deleted_at=datetime.now(timezone.utc), deleted_by=deleted_by)
        )
        await db.flush()
        return result.rowcount > 0

    @staticmethod
    async def restore(db: AsyncSession, log_id: uuid.UUID) -> bool:
        result = await db.execute(
            update(OperationLog)
            .where(OperationLog.id == log_id, OperationLog.is_deleted == True)
            .values(is_deleted=False, deleted_at=None, deleted_by=None)
        )
        await db.flush()
        return result.rowcount > 0

    @staticmethod
    async def hard_delete(db: AsyncSession, log_id: uuid.UUID) -> bool:
        result = await db.execute(sql_delete(OperationLog).where(OperationLog.id == log_id))
        await db.flush()
        return result.rowcount > 0

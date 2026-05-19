import os
import uuid
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import UploadFile
from app.config import settings
from app.models.file import File


class FileService:
    @staticmethod
    async def get_list(db: AsyncSession, page: int = 1, page_size: int = 10):
        query = select(File).order_by(File.created_at.desc())
        count_query = select(func.count(File.id))
        total = (await db.execute(count_query)).scalar()
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return result.scalars().all(), total

    @staticmethod
    async def get_by_id(db: AsyncSession, file_id: uuid.UUID) -> File | None:
        result = await db.execute(select(File).where(File.id == file_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def upload(db: AsyncSession, upload_file: UploadFile, uploaded_by: uuid.UUID | None = None) -> File:
        # Validate size
        content = await upload_file.read()
        max_size = settings.FILE_MAX_SIZE_MB * 1024 * 1024
        if len(content) > max_size:
            raise ValueError(f"File size exceeds {settings.FILE_MAX_SIZE_MB}MB limit")

        # Generate unique storage name
        ext = os.path.splitext(upload_file.filename or "unnamed")[1]
        storage_name = f"{uuid.uuid4()}{ext}"
        storage_path = os.path.join(settings.FILE_STORAGE_PATH, storage_name)

        # Ensure storage directory exists
        os.makedirs(settings.FILE_STORAGE_PATH, exist_ok=True)

        # Write file
        with open(storage_path, "wb") as f:
            f.write(content)

        file_record = File(
            original_name=upload_file.filename or "unnamed",
            storage_name=storage_name,
            storage_path=storage_path,
            file_size=len(content),
            mime_type=upload_file.content_type,
            file_extension=ext.lstrip(".") if ext else None,
            storage_type=settings.FILE_STORAGE_TYPE,
            uploaded_by=uploaded_by,
        )
        db.add(file_record)
        await db.flush()
        return file_record

    @staticmethod
    async def delete(db: AsyncSession, file_record: File) -> None:
        # Delete physical file
        if os.path.exists(file_record.storage_path):
            os.remove(file_record.storage_path)
        await db.delete(file_record)
        await db.flush()

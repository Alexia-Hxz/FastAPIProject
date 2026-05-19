import uuid
from sqlalchemy import String, BigInteger, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin, UUIDMixin


class File(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "files"

    original_name: Mapped[str] = mapped_column(String(255))
    storage_name: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    file_size: Mapped[int] = mapped_column(BigInteger)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    file_extension: Mapped[str | None] = mapped_column(String(20))
    storage_type: Mapped[str] = mapped_column(String(20), default="local")
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column()
    download_count: Mapped[int] = mapped_column(Integer, default=0)

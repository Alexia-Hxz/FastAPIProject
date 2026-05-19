import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Integer, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, UUIDMixin


class OperationLog(Base, UUIDMixin):
    __tablename__ = "operation_logs"

    user_id: Mapped[uuid.UUID | None] = mapped_column()
    username: Mapped[str | None] = mapped_column(String(50))
    request_method: Mapped[str] = mapped_column(String(10))
    request_url: Mapped[str] = mapped_column(String(500))
    request_params: Mapped[dict | None] = mapped_column(JSON)
    request_body: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    response_status: Mapped[int] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int] = mapped_column(Integer)
    module: Mapped[str | None] = mapped_column(String(50))
    action: Mapped[str | None] = mapped_column(String(100))
    is_deleted: Mapped[bool] = mapped_column(default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

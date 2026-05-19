import uuid
from sqlalchemy import Boolean, String, Integer, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin, UUIDMixin


class Menu(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "menus"

    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("menus.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    menu_type: Mapped[str] = mapped_column(String(20), default="menu")  # menu | button | api
    path: Mapped[str | None] = mapped_column(String(200))
    component: Mapped[str | None] = mapped_column(String(200))
    icon: Mapped[str | None] = mapped_column(String(50))
    permission_code: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)

    children = relationship("Menu", backref="parent", remote_side="Menu.id", lazy="selectin")
    roles = relationship("Role", secondary="role_menus", back_populates="menus", lazy="selectin")


class RoleMenu(Base, UUIDMixin):
    __tablename__ = "role_menus"
    __table_args__ = (UniqueConstraint("role_id", "menu_id"),)

    role_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    menu_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("menus.id", ondelete="CASCADE"), nullable=False)

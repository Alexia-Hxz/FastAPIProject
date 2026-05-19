"""Initialize database with admin user, roles, and menus."""
import asyncio
import uuid
from sqlalchemy import select
from app.core.database import async_session, engine
from app.core.security import hash_password
from app.models.base import Base
from app.models.user import User
from app.models.role import Role, UserRole
from app.models.menu import Menu, RoleMenu


MENU_DATA = [
    {"name": "系统管理", "menu_type": "menu", "path": "/system", "icon": "setting", "sort_order": 1, "children": [
        {"name": "用户管理", "menu_type": "menu", "path": "/system/users", "permission_code": "user:list", "sort_order": 1, "children": [
            {"name": "创建用户", "menu_type": "button", "permission_code": "user:create", "sort_order": 1},
            {"name": "查看用户", "menu_type": "button", "permission_code": "user:read", "sort_order": 2},
            {"name": "更新用户", "menu_type": "button", "permission_code": "user:update", "sort_order": 3},
            {"name": "删除用户", "menu_type": "button", "permission_code": "user:delete", "sort_order": 4},
            {"name": "分配角色", "menu_type": "button", "permission_code": "user:assign", "sort_order": 5},
        ]},
        {"name": "角色管理", "menu_type": "menu", "path": "/system/roles", "permission_code": "role:list", "sort_order": 2, "children": [
            {"name": "创建角色", "menu_type": "button", "permission_code": "role:create", "sort_order": 1},
            {"name": "查看角色", "menu_type": "button", "permission_code": "role:read", "sort_order": 2},
            {"name": "更新角色", "menu_type": "button", "permission_code": "role:update", "sort_order": 3},
            {"name": "删除角色", "menu_type": "button", "permission_code": "role:delete", "sort_order": 4},
            {"name": "分配菜单", "menu_type": "button", "permission_code": "role:assign", "sort_order": 5},
        ]},
        {"name": "菜单管理", "menu_type": "menu", "path": "/system/menus", "permission_code": "menu:list", "sort_order": 3, "children": [
            {"name": "创建菜单", "menu_type": "button", "permission_code": "menu:create", "sort_order": 1},
            {"name": "更新菜单", "menu_type": "button", "permission_code": "menu:update", "sort_order": 2},
            {"name": "删除菜单", "menu_type": "button", "permission_code": "menu:delete", "sort_order": 3},
        ]},
    ]},
    {"name": "AI 助手", "menu_type": "menu", "path": "/ai", "icon": "cpu", "sort_order": 2, "children": [
        {"name": "AI 对话", "menu_type": "menu", "path": "/ai/chat", "permission_code": "ai:chat", "sort_order": 1},
        {"name": "NL2SQL查询", "menu_type": "menu", "path": "/ai/nl2sql", "permission_code": "ai:nl2sql", "sort_order": 2},
        {"name": "代码生成器", "menu_type": "menu", "path": "/ai/codegen", "permission_code": "codegen:use", "sort_order": 3},
        {"name": "日志分析", "menu_type": "menu", "path": "/ai/log-analysis", "permission_code": "log:analysis", "sort_order": 4},
    ]},
    {"name": "监控管理", "menu_type": "menu", "path": "/monitor", "icon": "monitor", "sort_order": 3, "children": [
        {"name": "操作日志", "menu_type": "menu", "path": "/monitor/logs", "permission_code": "log:list", "sort_order": 1, "children": [
            {"name": "查看详情", "menu_type": "button", "permission_code": "log:read", "sort_order": 1},
        ]},
        {"name": "文件管理", "menu_type": "menu", "path": "/monitor/files", "permission_code": "file:list", "sort_order": 2, "children": [
            {"name": "上传文件", "menu_type": "button", "permission_code": "file:upload", "sort_order": 1},
            {"name": "下载文件", "menu_type": "button", "permission_code": "file:download", "sort_order": 2},
            {"name": "删除文件", "menu_type": "button", "permission_code": "file:delete", "sort_order": 3},
        ]},
    ]},
]


async def create_menu_tree(db, items, parent_id=None):
    menus = []
    for item in items:
        children = item.pop("children", [])
        menu = Menu(parent_id=parent_id, **item)
        db.add(menu)
        await db.flush()
        if children:
            await create_menu_tree(db, children, menu.id)
        menus.append(menu)
    return menus


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        # Create admin role
        result = await db.execute(select(Role).where(Role.code == "admin"))
        admin_role = result.scalar_one_or_none()
        if not admin_role:
            admin_role = Role(name="系统管理员", code="admin", description="拥有所有权限")
            db.add(admin_role)
            await db.flush()

        # Create user role
        result = await db.execute(select(Role).where(Role.code == "user"))
        user_role = result.scalar_one_or_none()
        if not user_role:
            user_role = Role(name="普通用户", code="user", description="基础权限")
            db.add(user_role)
            await db.flush()

        # Create menus
        result = await db.execute(select(Menu).limit(1))
        if not result.scalar_one_or_none():
            all_menus = await create_menu_tree(db, MENU_DATA)

        # Create admin user
        result = await db.execute(select(User).where(User.username == "admin"))
        admin_user = result.scalar_one_or_none()
        if not admin_user:
            admin_user = User(
                username="admin",
                password_hash=hash_password("admin123"),
                email="admin@example.com",
                nickname="管理员",
                is_superuser=True,
            )
            db.add(admin_user)
            await db.flush()
            db.add(UserRole(user_id=admin_user.id, role_id=admin_role.id))
            await db.flush()

        # Assign all menus to admin role
        result = await db.execute(select(Menu))
        all_menus = result.scalars().all()
        for menu in all_menus:
            result = await db.execute(
                select(RoleMenu).where(RoleMenu.role_id == admin_role.id, RoleMenu.menu_id == menu.id)
            )
            if not result.scalar_one_or_none():
                db.add(RoleMenu(role_id=admin_role.id, menu_id=menu.id))
        await db.flush()

        await db.commit()

        print("Seed completed successfully!")
        print("  Admin user: admin / admin123")
        print("  Roles: admin, user")
        print(f"  Menus: {len(all_menus)} items")


if __name__ == "__main__":
    asyncio.run(seed())

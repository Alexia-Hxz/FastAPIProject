# CLAUDE.md

此文件为 Claude Code（claude.ai/code）在本仓库中工作时提供指导。

## 开发命令

```bash
# 启动基础设施（需要 Docker Desktop 运行）
docker compose up -d postgres redis

# 首次使用：初始化数据库（创建 admin/admin123、角色、菜单）
PYTHONPATH=. .venv/Scripts/python scripts/seed.py

# 启动开发服务器（热重载）
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 运行全部测试（内存 SQLite + FakeRedis，无需 Docker）
.venv/Scripts/python -m pytest tests/ -v

# 运行单个测试文件
.venv/Scripts/python -m pytest tests/test_auth.py -v
```

管理员账号：`admin / admin123`

## 架构

**混合开发模式**：应用代码在本地 `.venv` 中运行（热重载）；PostgreSQL 16 + Redis 7 在 Docker 容器中运行（`docker-compose.yml`）。备选：如果 `DB_HOST` 环境变量为空，`config.py` 会自动回退到本地 SQLite（`sqlite+aiosqlite`）——零依赖模式，适合快速启动。

**数据库 URL 解析**（`app/config.py`）：`DATABASE_URL` 环境变量 → 通过 `DB_HOST`/`DB_USER` 等拼接 PostgreSQL 连接串 → 项目根目录 SQLite 文件。只读引擎与主引擎相同，除非单独设置 `READONLY_DATABASE_URL`。

**Redis**（`app/core/redis.py`）：懒加载单例，优雅降级。如果 Redis 不可达，`get_redis()` 返回 `None`，`dependencies.py` 中的 token 黑名单检查自动跳过。测试使用 `FakeRedis` 字典模拟。

**认证流程**（`app/dependencies.py`）：
1. `get_token_from_header` — 提取 Bearer token，缺失/格式错误返回 401
2. `get_current_user` — 检查 Redis 黑名单（Redis 不可用时跳过），解码 JWT，从数据库获取 User
3. `require_permission(code)` — 工厂函数，返回 FastAPI 依赖；超管跳过所有检查

**RBAC 模型**：User → Role（多对多，通过 `user_roles` 关联表）→ Menu（多对多，通过 `role_menus` 关联表）。Menu 为树形结构（`parent_id` 自引用），每个节点可有 `permission_code` 权限码。前端从 `/menus/user` 接口收集权限码，通过 `v-if="hasPerm('code')"` 控制 UI 显隐。

**测试机制**（`tests/conftest.py`）：使用 FastAPI 的 `dependency_overrides` 将 `get_db` 替换为内存 SQLite，将 `get_redis` 替换为 `FakeRedis`。每个测试通过 `setup_db` autouse fixture 获得全新数据库（测试前 create_all，测试后 drop_all）。`client` fixture 提供通过 `ASGITransport` 连接到 FastAPI 应用的 `httpx.AsyncClient`。

**NL2SQL 管道**（`app/services/nl2sql_service.py`）：用户自然语言 → LLM 生成 SQL → `sqlglot` 解析/校验 → 通过 `get_readonly_db()` 在只读事务中执行。安全措施：最大行数限制（`NL2SQL_MAX_RESULT_ROWS`）、查询超时（`NL2SQL_QUERY_TIMEOUT_MS`）、仅允许 SELECT 语句。

**操作日志中间件**（`app/middleware/operation_log.py`）：ASGI 中间件，非 FastAPI 中间件——在协议层捕获请求和响应。记录请求方法、路径、状态码、耗时、客户端 IP、用户 ID（来自 `request.state`）。只记录 API 路由，跳过静态文件和健康检查。

**前端**（`static/index.html`）：Vue 3 + Element Plus 单文件 SPA，通过 CDN 引入，无需构建步骤。核心函数：`api(path, opts)` 通用 HTTP 请求（401 自动跳转登录）、`hasPerm(code)` 按钮权限控制、`showUserDialog(row)` / `showRoleForm(row)` CRUD 弹窗。

## 初始数据

`scripts/seed.py` 创建：管理员用户（超管）、admin 角色、user 角色、完整菜单树（约 40 个节点，覆盖系统管理、AI 功能、监控管理）。admin 角色获得全部菜单授权。脚本幂等，可重复执行。

## 已知约束

- Docker 构建时容器内 `pip install` 可能超时（清华镜像），使用混合模式可规避
- `uvicorn --reload` 仅监控 `.py` 文件，HTML 修改需手动刷新浏览器
- `.env` 含 API Key，在 `.gitignore` 中，绝不提交
- DeepSeek API 不支持视觉/多模态；代码中预留了 `vision` 格式字段但实际不可用

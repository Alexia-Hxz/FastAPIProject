# AI-Admin — FastAPI 智能后台管理系统

基于 FastAPI 的全异步后台管理系统框架，集成 LLM 实现 NL2SQL 自然语言数据查询和 AI 操作助手。

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-async-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
## 功能

- **认证授权**: JWT 双 Token + Redis 黑名单
- **RBAC 权限**: 用户 → 角色 → 菜单/权限码 三级控制
- **用户/角色/菜单管理**: CRUD + 树形菜单 + 权限分配
- **操作日志**: 中间件自动记录，支持多条件筛选
- **文件管理**: 上传/下载/删除，本地存储
- **AI NL2SQL**: 自然语言转 SQL，sqlglot 安全校验
- **AI 助手**: SSE 流式对话 + 智能日志分析
- **代码生成器**: 根据表结构自动生成 CRUD 代码

## 技术栈

| 层 | 技术 |
|---|------|
| Web 框架 | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| AI SDK | openai (DeepSeek / 通义千问) |
| SQL 校验 | sqlglot |
| 部署 | Docker Compose |

## 快速启动

```bash
# 1. 启动服务 (PostgreSQL + Redis + App)
docker compose up -d

# 2. 初始化数据
docker compose exec app python scripts/seed.py

# 3. 访问 API 文档
# http://localhost:8000/docs

# 4. 登录
# 管理员账号: admin / admin123
```

## 本地开发

```bash
# 1. 启动 PostgreSQL + Redis
docker compose up -d postgres redis

# 2. 安装依赖
pip install -r requirements.txt

# 3. 复制配置文件
cp .env.example .env

# 4. 初始化数据库
# Linux/Mac:
python scripts/seed.py
# Windows (PowerShell):
$env:PYTHONPATH="."; python scripts/seed.py

# 5. 启动开发服务器
uvicorn app.main:app --reload
```

## AI 功能配置

编辑 `.env` 文件，配置 AI 提供商 API Key：

```env
# 推荐: DeepSeek (中文强、价格低)
AI_ENABLED=true
AI_API_KEY=sk-your-deepseek-api-key
AI_BASE_URL=https://api.deepseek.com/v1
AI_MODEL=deepseek-chat

# 或使用通义千问
# AI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
# AI_MODEL=qwen-turbo
```

## API 接口

### 认证 (/api/v1/auth)
- `POST /login` — 登录
- `POST /logout` — 登出
- `POST /refresh` — 刷新 Token
- `GET /me` — 当前用户信息
- `PUT /me/password` — 修改密码

### 用户管理 (/api/v1/users)
- `GET /` — 用户列表 (分页+搜索)
- `POST /` — 创建用户
- `GET /{id}` — 用户详情
- `PUT /{id}` — 更新用户
- `DELETE /{id}` — 删除用户
- `PUT /{id}/roles` — 分配角色

### 角色管理 (/api/v1/roles)
- `GET /` — 角色列表
- `POST /` — 创建角色
- `GET /{id}` — 角色详情
- `PUT /{id}` — 更新角色
- `DELETE /{id}` — 删除角色
- `PUT /{id}/menus` — 分配菜单

### 菜单管理 (/api/v1/menus)
- `GET /tree` — 菜单树
- `GET /user` — 当前用户菜单
- `POST /` — 创建菜单
- `PUT /{id}` — 更新菜单
- `DELETE /{id}` — 删除菜单

### AI 功能 (/api/v1/ai)
- `POST /chat` — AI 对话 (SSE 流式)
- `POST /nl2sql` — 自然语言查询
- `GET /chat/history` — 对话历史
- `GET /nl2sql/history` — NL2SQL 历史
- `POST /log-analysis` — 日志分析

### 其它
- `GET /api/v1/logs` — 操作日志
- `POST /api/v1/files/upload` — 上传文件
- `POST /api/v1/codegen/generate` — 代码生成

## 项目结构

```
app/
├── main.py          # 应用入口
├── config.py        # 配置管理
├── dependencies.py  # 依赖注入
├── api/v1/          # 路由层
├── models/          # ORM 模型
├── schemas/         # Pydantic 模型
├── services/        # 业务逻辑
├── core/            # 基础设施
└── middleware/       # 中间件
```

## 架构与安全设计

```
请求 → CORS → 限流（rate_limit）→ 操作日志（operation_log）
     → 依赖注入（dependencies：当前用户 / 权限码校验）
     → 路由层 api/v1 → 服务层 services → ORM（SQLAlchemy 2.0 async）
                                        ↕  PostgreSQL 16 / Redis 7
```

- **认证**：JWT Access + Refresh 双 Token，登出写入 Redis 黑名单，实现即时失效
- **授权**：用户 → 角色 → 菜单/权限码 三级 RBAC，权限校验在路由入口通过依赖注入完成
- **NL2SQL 安全链路**：自然语言 → LLM 生成 SQL → **sqlglot 解析校验**（仅允许只读语句，拦截多语句与危险关键字）→ 参数化执行 → 结构化结果，不让模型直接对数据库说话
- **AI 助手**：SSE 流式输出，支持对话历史与智能日志分析
- **可观测性**：操作日志中间件自动记录请求关键信息，支持多条件筛选

## 截图

<!-- 截图待上传：把 PNG 放进 docs/screenshots/ 后取消下面的注释 -->
<!--
![接口文档](docs/screenshots/01-docs.png)
![NL2SQL 查询](docs/screenshots/02-nl2sql.png)
![RBAC 权限管理](docs/screenshots/03-rbac.png)
-->

## 安全提示

仓库中的数据库密码（示例值 aiadmin123）与默认管理员账号（admin / admin123）**仅供本地演示**；部署到公开环境前必须修改为独立密钥与强口令。
## 测试

```bash
pytest -v
```
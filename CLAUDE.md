# AI-Admin 项目速查

## 启动方式

```bash
# 1. 启动基础设施（Docker Desktop 需在运行）
docker compose up -d postgres redis

# 2. 初始化数据库（首次）
$env:PYTHONPATH="."; python scripts/seed.py

# 3. 启动开发服务器
.venv/Scripts/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

管理员：admin / admin123

## 当前架构

- **混合模式**：应用代码本地 .venv 运行（热重载），PostgreSQL + Redis 在 Docker Desktop 容器中
- **备选**：清空 DB_HOST 回退 SQLite（零依赖）
- 全 Docker 部署：`docker compose up -d`（Dockerfile 中 pip 镜像在国内可能超时）

## 项目结构

```
app/
├── main.py          # 入口，lifespan 自动建表
├── config.py        # .env 配置，DB_HOST 为空则走 SQLite
├── dependencies.py  # get_current_user, require_permission, get_token_from_header
├── api/v1/          # auth, users, roles, menus, logs, files, ai, codegen
├── models/          # User, Role, Menu, OperationLog, File, AIConversation, NL2SQLQuery
├── schemas/         # Pydantic 请求/响应模型
├── services/        # 业务逻辑
├── core/            # database, redis, security, exceptions
└── middleware/       # CORS, 操作日志(ASGI), 速率限制
static/index.html    # 整个前端（Vue3 + Element Plus CDN，单文件）
scripts/seed.py      # 初始数据
```

## 前端关键函数速查

| 函数 | 作用 |
|------|------|
| `hasPerm(code)` | 检查当前用户是否有某权限码（v-if 控制按钮显隐） |
| `showRoleForm(row)` | 打开角色编辑弹窗（内含菜单树），row=null 为新增 |
| `saveRole()` | 保存角色 → 自动提交菜单权限 |
| `showUserDialog(row)` | 打开用户编辑弹窗（内含角色选择），row=null 为新增 |
| `saveUser()` | 保存用户 → 自动提交角色分配 |
| `api(path, opts)` | 通用 API 调用，401 自动登出 |

## 权限体系（RBAC）

user → role → menu（树形，每节点有 permission_code）→ 超管跳过所有检查
后端：`Depends(require_permission("xxx"))`
前端：`v-if="hasPerm('xxx')"`，权限码从 `/menus/user` 返回的菜单树收集

## 最近改动摘要

1. 用户创建/编辑弹窗：集成角色多选框，保存时自动分配
2. 角色编辑弹窗：集成菜单权限树，保存时自动提交（删除了独立的"分配菜单"入口）
3. 前端按钮级权限控制：所有操作按钮通过 hasPerm 显隐
4. AI 对话注入用户身份：`_build_user_context()` 拼入系统提示词最前面
5. 密码输入框全部加 show-password
6. 操作日志：状态码筛选扩充到 9 种，请求方法去掉了 DELETE
7. Auth Header 缺失返回 401 而非 422
8. 新增 GET /users/{id}/roles 接口

## 已知注意事项

- Dockerfile 中清华 pip 镜像在国内 Docker 容器内可能超时，混合模式不受影响
- uvicorn `--reload` 只监控 Python 文件，HTML 修改需手动刷新浏览器
- .env 含 API Key，在 .gitignore 中，不会提交
- DeepSeek 不支持图片多模态，代码已预留 vision 格式

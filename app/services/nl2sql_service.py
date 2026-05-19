import time
import uuid
import re
import sqlglot
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.config import settings
from app.models.base import Base
from app.models.ai_conversation import NL2SQLQuery

FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
    "CREATE", "GRANT", "REVOKE", "EXEC", "COPY", "VACUUM",
    "BEGIN", "COMMIT", "ROLLBACK", "TRANSACTION",
}

COLUMN_CN = {
    "id": "ID", "username": "用户名", "password_hash": "密码哈希", "nickname": "昵称",
    "email": "邮箱", "phone": "手机", "is_active": "是否启用", "is_superuser": "是否超管",
    "created_at": "创建时间", "updated_at": "更新时间",
    "name": "名称", "code": "代码", "description": "描述",
    "parent_id": "父ID", "menu_type": "菜单类型", "path": "路径",
    "permission_code": "权限码", "icon": "图标", "sort_order": "排序",
    "is_visible": "是否可见",
    "user_id": "用户ID", "role_id": "角色ID", "menu_id": "菜单ID",
    "request_method": "请求方法", "request_url": "请求URL",
    "request_params": "请求参数", "request_body": "请求体",
    "ip_address": "IP地址", "user_agent": "用户代理",
    "response_status": "响应状态码", "error_message": "错误信息",
    "duration_ms": "耗时(ms)", "module": "模块", "action": "操作",
    "is_deleted": "是否删除", "deleted_at": "删除时间", "deleted_by": "删除者",
    "original_name": "原始文件名", "storage_name": "存储名", "storage_path": "存储路径",
    "file_size": "文件大小", "mime_type": "MIME类型", "file_extension": "扩展名",
    "storage_type": "存储类型", "uploaded_by": "上传者", "download_count": "下载次数",
    "session_id": "会话ID", "role": "角色", "content": "内容",
    "model": "模型", "token_count": "Token数", "token_used": "Token使用",
    "attachments": "附件",
    "natural_query": "自然语言查询", "generated_sql": "生成SQL",
    "is_success": "是否成功", "result_row_count": "结果行数",
    "execution_time_ms": "执行耗时(ms)",
    "avatar_url": "头像URL", "last_login_at": "最后登录时间",
    "component": "前端组件",
}

SENSITIVE_COLUMNS = {"password_hash", "password", "secret", "token"}


class NL2SQLService:
    @staticmethod
    def _get_schema_context() -> str:
        """Get schema from SQLAlchemy metadata (no DB connection needed)."""
        lines = []
        for table_name, table in Base.metadata.tables.items():
            cols_desc = []
            for col in table.columns:
                if col.name in SENSITIVE_COLUMNS:
                    continue
                cols_desc.append(f"    {col.name} {str(col.type)}")
            lines.append(f"  Table: {table_name}")
            lines.extend(cols_desc)
        return "\n".join(lines)

    @staticmethod
    def _validate_sql(sql: str) -> None:
        """Validate generated SQL for safety."""
        sql_upper = sql.upper().strip()

        # Check forbidden keywords
        for keyword in FORBIDDEN_KEYWORDS:
            if re.search(rf"\b{keyword}\b", sql_upper):
                raise ValueError(f"Forbidden SQL keyword detected: {keyword}")

        # Parse with sqlglot
        try:
            parsed = sqlglot.parse_one(sql, read="postgres")
        except Exception:
            raise ValueError("Invalid SQL syntax")

        # Ensure it's a SELECT statement
        if parsed.key != "select":
            raise ValueError("Only SELECT statements are allowed")

        # Check for multiple statements
        if ";" in sql.rstrip(";"):
            raise ValueError("Multiple SQL statements are not allowed")

    @staticmethod
    def _sanitize_results(columns: list[str], rows: list[tuple]) -> dict:
        """Remove sensitive columns and translate headers to Chinese."""
        safe_columns = [c for c in columns if c.lower() not in SENSITIVE_COLUMNS]
        safe_indices = [i for i, c in enumerate(columns) if c.lower() not in SENSITIVE_COLUMNS]
        safe_rows = [[row[i] for i in safe_indices] for row in rows]
        cn_columns = [COLUMN_CN.get(c.lower(), c) for c in safe_columns]
        return {"columns": cn_columns, "rows": safe_rows, "row_count": len(safe_rows)}

    @staticmethod
    async def execute_nl2sql(
        db: AsyncSession,
        readonly_db: AsyncSession,
        user_id: uuid.UUID,
        natural_query: str,
    ) -> dict:
        """Main NL2SQL pipeline."""
        start_time = time.time()
        query_record = NL2SQLQuery(
            user_id=user_id,
            natural_query=natural_query,
            generated_sql="",
            is_success=False,
        )

        try:
            # Step 1: Get schema context
            schema_ctx = NL2SQLService._get_schema_context()

            # Step 2: Generate SQL using LLM
            generated_sql = await NL2SQLService._generate_sql(natural_query, schema_ctx)
            query_record.generated_sql = generated_sql

            # Step 3: Validate SQL
            NL2SQLService._validate_sql(generated_sql)

            # Step 4: Execute on read-only connection
            result = await readonly_db.execute(
                text(generated_sql).execution_options(
                    timeout=settings.NL2SQL_QUERY_TIMEOUT_MS / 1000
                )
            )
            columns = list(result.keys())
            rows = result.fetchall()
            # Limit results
            if len(rows) > settings.NL2SQL_MAX_RESULT_ROWS:
                rows = rows[:settings.NL2SQL_MAX_RESULT_ROWS]

            elapsed_ms = int((time.time() - start_time) * 1000)
            query_record.is_success = True
            query_record.result_row_count = len(rows)
            query_record.execution_time_ms = elapsed_ms

            # Store record
            db.add(query_record)
            await db.flush()

            return {
                **NL2SQLService._sanitize_results(columns, rows),
                "generated_sql": generated_sql,
                "execution_time_ms": elapsed_ms,
            }

        except Exception as e:
            query_record.is_success = False
            query_record.error_message = str(e)
            query_record.execution_time_ms = int((time.time() - start_time) * 1000)
            db.add(query_record)
            await db.flush()
            raise

    @staticmethod
    async def _generate_sql(natural_query: str, schema_ctx: str) -> str:
        """Call LLM to generate SQL."""
        if not settings.AI_API_KEY:
            raise ValueError("AI_API_KEY is not configured")

        client = AsyncOpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
        )

        system_prompt = (
            "You are a SQL expert. Generate a PostgreSQL SELECT query based on the user's natural language request.\n\n"
            "Rules:\n"
            "1. ONLY generate SELECT queries\n"
            "2. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE, or any DDL/DML other than SELECT\n"
            "3. Use LIMIT to keep result sets manageable (max 1000 rows)\n"
            "4. Return ONLY the SQL statement, no explanations\n"
            "5. Use proper PostgreSQL syntax\n"
            "6. Do NOT query the password_hash column\n\n"
            "Database Schema:\n"
            f"{schema_ctx}"
        )

        response = await client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Generate SQL for: {natural_query}"},
            ],
            temperature=0.1,
            max_tokens=settings.AI_MAX_TOKENS,
        )

        sql = response.choices[0].message.content.strip()
        # Remove markdown code block if present
        if sql.startswith("```"):
            sql = sql.split("```")[1]
            if sql.startswith("sql"):
                sql = sql[3:]
        return sql.strip()

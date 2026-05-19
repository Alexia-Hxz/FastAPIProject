import json
import uuid
import logging
import base64
import os
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from openai import AsyncOpenAI
from app.config import settings
from app.models.ai_conversation import AIConversation
from app.models.operation_log import OperationLog

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = (
    "You are a helpful AI assistant integrated into 'AI-Admin', an admin management system. "
    "You can answer general questions (math, knowledge, casual conversation) as well as help with:\n"
    "1. Understanding system features and how to use them\n"
    "2. Analyzing data presented in the system\n"
    "3. Troubleshooting common issues\n"
    "4. Providing insights from operation logs and user data\n\n"
    "Be concise, professional, and helpful. Answer in Chinese when the user speaks Chinese.\n"
    "IMPORTANT: Do NOT use Markdown formatting (no **bold**, no # headings, no `code blocks`, no ``` fences, no *italics*, no - lists). Output plain text only."
)

TEXT_EXTENSIONS = {".txt", ".json", ".csv", ".md", ".py", ".js", ".ts", ".html", ".css",
                   ".sql", ".yaml", ".yml", ".xml", ".log", ".env", ".cfg", ".ini",
                   ".sh", ".bat", ".ps1", ".java", ".go", ".rs", ".c", ".cpp", ".h",
                   ".rb", ".php"}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}

TEXT_MAX_CHARS = 50000


class AIService:
    @staticmethod
    def _get_client() -> AsyncOpenAI:
        if not settings.AI_API_KEY:
            raise ValueError("AI_API_KEY is not configured")
        return AsyncOpenAI(
            api_key=settings.AI_API_KEY,
            base_url=settings.AI_BASE_URL,
        )

    @staticmethod
    async def chat(
        user_id: uuid.UUID,
        session_id: str,
        message: str,
        file_ids: list[str] | None = None,
    ) -> AsyncGenerator[str, None]:
        from app.core.database import async_session as chat_session

        client = AIService._get_client()

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        try:
            async with chat_session() as db:
                history = await AIService.get_chat_history(db, user_id, session_id, limit=20)
                for h in history:
                    messages.append({"role": h.role, "content": h.content})
        except Exception:
            logger.exception("Failed to load chat history")

        if file_ids:
            try:
                async with chat_session() as db:
                    text_context, _, _ = await AIService._build_file_context(db, file_ids)
                if text_context:
                    message = f"{text_context}\n\n---\n{message}"
            except Exception:
                logger.exception("Failed to build file context")

        messages.append({"role": "user", "content": message})

        response = await client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=messages,
            temperature=settings.AI_TEMPERATURE,
            max_tokens=settings.AI_MAX_TOKENS,
            stream=True,
        )

        full_content = ""
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_content += token
                yield json.dumps({"type": "token", "content": token}) + "\n"

        yield json.dumps({"type": "done", "content": full_content}) + "\n"

    @staticmethod
    async def save_message(
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: str,
        role: str,
        content: str,
        attachments: list | None = None,
    ) -> AIConversation:
        conv = AIConversation(
            user_id=user_id,
            session_id=session_id,
            role=role,
            content=content,
            attachments=attachments,
        )
        db.add(conv)
        await db.flush()
        return conv

    @staticmethod
    async def get_chat_history(
        db: AsyncSession,
        user_id: uuid.UUID,
        session_id: str,
        limit: int = 50,
    ):
        result = await db.execute(
            select(AIConversation)
            .where(AIConversation.user_id == user_id, AIConversation.session_id == session_id)
            .order_by(AIConversation.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        rows.reverse()
        return rows

    @staticmethod
    def _compute_stats(logs: list) -> dict:
        if not logs:
            return {"total": 0, "errors": 0, "methods": {}, "avg_duration": 0}
        total = len(logs)
        errors = sum(1 for l in logs if l.response_status >= 400)
        methods = {}
        for log in logs:
            methods[log.request_method] = methods.get(log.request_method, 0) + 1
        return {
            "total": total,
            "errors": errors,
            "methods": methods,
            "avg_duration": round(sum(l.duration_ms for l in logs) / total),
        }

    @staticmethod
    async def _build_file_context(db: AsyncSession, file_ids: list[str]) -> tuple[str, list[dict], list[dict]]:
        from app.models.file import File

        text_parts = []
        image_blocks = []
        attachments_meta = []

        for fid in file_ids:
            try:
                file_uuid = uuid.UUID(fid)
            except ValueError:
                continue

            result = await db.execute(select(File).where(File.id == file_uuid))
            file_record = result.scalar_one_or_none()
            if not file_record or not os.path.exists(file_record.storage_path):
                text_parts.append(f"[文件不存在或已被删除: {fid}]")
                continue

            ext = os.path.splitext(file_record.original_name)[1].lower()
            meta = {
                "id": str(file_record.id),
                "original_name": file_record.original_name,
                "file_size": file_record.file_size,
                "mime_type": file_record.mime_type,
                "file_extension": file_record.file_extension,
            }
            attachments_meta.append(meta)

            if ext in TEXT_EXTENSIONS:
                try:
                    with open(file_record.storage_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(file_record.storage_path, "r", encoding="latin-1") as f:
                        content = f.read()
                if len(content) > TEXT_MAX_CHARS:
                    content = content[:TEXT_MAX_CHARS]
                    text_parts.append(f"[文件: {file_record.original_name}（内容已截断至 50KB）]\n{content}")
                else:
                    text_parts.append(f"[文件: {file_record.original_name}]\n{content}")

            elif ext in IMAGE_EXTENSIONS:
                text_parts.append(f"[用户分享了图片: {file_record.original_name}（{file_record.file_size / 1024:.1f}KB）]")
            else:
                text_parts.append(f"[用户分享了文件: {file_record.original_name}]")

        text_context = "\n\n".join(text_parts) if text_parts else ""
        return text_context, image_blocks, attachments_meta

    @staticmethod
    async def get_log_stats(
        db: AsyncSession,
        hours: int = 24,
    ) -> dict:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(OperationLog).where(OperationLog.created_at >= cutoff).limit(500)
        )
        return AIService._compute_stats(result.scalars().all())

    @staticmethod
    async def analyze_logs(
        user_id: uuid.UUID,
        db: AsyncSession,
        hours: int = 24,
    ) -> AsyncGenerator[str, None]:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = await db.execute(
            select(OperationLog).where(OperationLog.created_at >= cutoff).limit(500)
        )
        logs = result.scalars().all()

        if not logs:
            yield json.dumps({"type": "error", "content": "No logs found in the specified time range"}) + "\n"
            return

        stats = AIService._compute_stats(logs)
        yield json.dumps({
            "type": "stats", "total": stats["total"],
            "errors": stats["errors"], "avg_duration": stats["avg_duration"],
        }) + "\n"

        error_rate = stats["errors"] / stats["total"] * 100 if stats["total"] else 0
        summary = f"""请分析以下系统操作日志数据：

- 统计周期：最近 {hours} 小时
- 总请求数：{stats["total"]}
- 异常请求数：{stats["errors"]}/{stats["total"]}，错误率 {error_rate:.1f}%
- HTTP 方法分布：{stats["methods"]}
- 平均响应耗时：{stats["avg_duration"]}ms

最近的请求 URL：
{chr(10).join(f"  - {l.request_method} {l.request_url} (状态码 {l.response_status})" for l in logs[:20])}

请用中文简要分析是否存在异常模式、安全风险或需要关注的问题。按以下结构输出（注意：不要使用 Markdown 格式，直接输出纯文本）：

1. 整体概况
2. 异常检测
3. 安全风险
4. 建议"""

        client = AIService._get_client()
        response = await client.chat.completions.create(
            model=settings.AI_MODEL,
            messages=[
                {"role": "system", "content": "你是一名专业的系统日志分析专家。请用中文分析日志数据，提供有价值的见解和实用建议。输出要简洁、结构化。注意：不要使用 Markdown 格式（不要用 ** 加粗、# 标题、` 代码等），直接输出纯文本。"},
                {"role": "user", "content": summary},
            ],
            temperature=0.3,
            max_tokens=settings.AI_MAX_TOKENS,
            stream=True,
        )

        full_content = ""
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_content += token
                yield json.dumps({"type": "token", "content": token}) + "\n"

        yield json.dumps({"type": "done", "content": full_content}) + "\n"

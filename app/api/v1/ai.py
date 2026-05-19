import json
import uuid
import logging
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db, get_readonly_db
from app.dependencies import get_current_user, require_permission
from app.models.user import User
from app.schemas.common import ResponseModel, PageResponse, PageInfo
from app.services.ai_service import AIService
from app.services.nl2sql_service import NL2SQLService
from app.models.ai_conversation import AIConversation, NL2SQLQuery

logger = logging.getLogger(__name__)


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    stream: bool = True
    file_ids: list[str] | None = None


router = APIRouter(prefix="/ai", tags=["AI 助手"])


@router.post("/chat")
async def ai_chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("ai:chat")),
    db: AsyncSession = Depends(get_db),
):
    if not body.message.strip():
        return ResponseModel(code=400, message="Message is required", data=None)

    from app.core.database import async_session as stream_session

    attachments_meta = []
    if body.file_ids:
        try:
            _, _, attachments_meta = await AIService._build_file_context(db, body.file_ids)
        except Exception:
            logger.exception("Failed to build file context for saving")

    if body.stream:
        async def event_stream():
            done_content = None
            try:
                async for line in AIService.chat(current_user.id, body.session_id, body.message, body.file_ids):
                    yield f"data: {line}\n\n"
                    if done_content is None:
                        try:
                            d = json.loads(line.strip())
                            if d.get("type") == "done":
                                done_content = d["content"]
                        except Exception:
                            pass

                if done_content:
                    async with stream_session() as save_db:
                        try:
                            await AIService.save_message(save_db, current_user.id, body.session_id, "user", body.message, attachments_meta if attachments_meta else None)
                            await AIService.save_message(save_db, current_user.id, body.session_id, "assistant", done_content)
                            await save_db.commit()
                        except Exception:
                            logger.exception("Failed to save messages (streaming)")
            except Exception:
                logger.exception("AI streaming error")
                yield f"data: {json.dumps({'type': 'error', 'content': 'AI service error'})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    try:
        full_reply = ""
        async for line in AIService.chat(current_user.id, body.session_id, body.message, body.file_ids):
            try:
                d = json.loads(line.strip())
                if d.get("type") == "token":
                    full_reply += d["content"]
                elif d.get("type") == "done":
                    full_reply = d["content"]
            except Exception:
                logger.exception("Failed to parse chat response line")

        if full_reply:
            async with stream_session() as save_db:
                try:
                    await AIService.save_message(save_db, current_user.id, body.session_id, "user", body.message, attachments_meta if attachments_meta else None)
                    await AIService.save_message(save_db, current_user.id, body.session_id, "assistant", full_reply)
                    await save_db.commit()
                except Exception:
                    logger.exception("Failed to save messages (non-streaming)")

        return ResponseModel(data={"reply": full_reply, "session_id": body.session_id})
    except Exception as e:
        logger.exception("AI chat error")
        return ResponseModel(code=500, message=f"AI error: {str(e)}", data=None)


@router.post("/nl2sql")
async def nl2sql(
    query: str = Query(..., description="Natural language query"),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("ai:nl2sql")),
    db: AsyncSession = Depends(get_db),
    readonly_db: AsyncSession = Depends(get_readonly_db),
):
    if not query.strip():
        return ResponseModel(code=400, message="Query is required", data=None)

    try:
        result = await NL2SQLService.execute_nl2sql(db, readonly_db, current_user.id, query)
        return ResponseModel(data=result)
    except ValueError as e:
        return ResponseModel(code=400, message=str(e), data=None)
    except Exception as e:
        return ResponseModel(code=500, message=f"NL2SQL error: {str(e)}", data=None)


@router.get("/chat/history")
async def chat_history(
    session_id: str = Query(default="default"),
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    history = await AIService.get_chat_history(db, current_user.id, session_id, limit)
    return ResponseModel(
        data=[{
            "id": str(h.id),
            "role": h.role,
            "content": h.content,
            "attachments": h.attachments,
            "created_at": str(h.created_at),
        } for h in history]
    )


@router.delete("/chat/history")
async def clear_chat_history(
    session_id: str = Query(default="default"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import delete as sql_delete
    await db.execute(
        sql_delete(AIConversation).where(
            AIConversation.user_id == current_user.id,
            AIConversation.session_id == session_id
        )
    )
    await db.commit()
    return ResponseModel(message="Chat history cleared")


@router.get("/nl2sql/history")
async def nl2sql_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import func, select

    total = (await db.execute(select(func.count(NL2SQLQuery.id)).where(NL2SQLQuery.user_id == current_user.id))).scalar()
    result = await db.execute(
        select(NL2SQLQuery)
        .where(NL2SQLQuery.user_id == current_user.id)
        .order_by(NL2SQLQuery.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    queries = result.scalars().all()

    return ResponseModel(
        data=PageResponse(
            items=[{
                "id": str(q.id),
                "natural_query": q.natural_query,
                "generated_sql": q.generated_sql,
                "is_success": q.is_success,
                "result_row_count": q.result_row_count,
                "execution_time_ms": q.execution_time_ms,
                "error_message": q.error_message,
                "created_at": str(q.created_at),
            } for q in queries],
            pagination=PageInfo(page=page, page_size=page_size, total=total),
        )
    )


@router.post("/log-analysis")
async def log_analysis(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("log:analysis")),
):
    async def event_stream():
        from app.core.database import async_session as stream_session
        try:
            async with stream_session() as db:
                async for line in AIService.analyze_logs(current_user.id, db, hours):
                    yield f"data: {line}\n\n"
        except Exception:
            logger.exception("Log analysis error")
            yield f"data: {json.dumps({'type': 'error', 'content': 'Log analysis error'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/log-analysis/preview")
async def log_analysis_preview(
    hours: int = Query(default=24, ge=1, le=168),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_readonly_db),
):
    """Return quick log stats without AI analysis."""
    try:
        from app.services.ai_service import AIService
        stats = await AIService.get_log_stats(db, hours)
        return ResponseModel(data=stats)
    except Exception as e:
        return ResponseModel(code=500, message=str(e), data=None)

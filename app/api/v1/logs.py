from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, parse_uuid
from app.models.user import User
from app.schemas.common import ResponseModel, PageResponse, PageInfo
from app.schemas.log import LogResponse, LogDetailResponse
from app.services.log_service import LogService

router = APIRouter(prefix="/logs", tags=["操作日志"])


@router.get("", response_model=ResponseModel[PageResponse[LogResponse]])
async def list_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    username: str | None = None,
    module: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    exclude_method: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("log:list")),
):
    logs, total = await LogService.get_list(
        db, page, page_size, username, module, method, status_code, start_time, end_time, exclude_method
    )
    items = [LogResponse.model_validate(l) for l in logs]
    return ResponseModel(data=PageResponse(items=items, pagination=PageInfo(page=page, page_size=page_size, total=total)))


@router.get("/recycle-bin", response_model=ResponseModel[PageResponse[LogResponse]])
async def list_deleted_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("log:list")),
):
    logs, total = await LogService.get_list(db, page, page_size, include_deleted=True)
    items = [LogResponse.model_validate(l) for l in logs]
    return ResponseModel(data=PageResponse(items=items, pagination=PageInfo(page=page, page_size=page_size, total=total)))


@router.get("/{log_id}", response_model=ResponseModel[LogDetailResponse])
async def get_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("log:read")),
):
    log = await LogService.get_by_id(db, parse_uuid(log_id))
    if not log:
        return ResponseModel(code=404, message="Log not found", data=None)
    return ResponseModel(data=LogDetailResponse.model_validate(log))


@router.delete("/{log_id}")
async def delete_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("log:list")),
):
    deleted = await LogService.soft_delete(db, parse_uuid(log_id), current_user.username or "unknown")
    if not deleted:
        return ResponseModel(code=404, message="Log not found", data=None)
    return ResponseModel(message="Log moved to recycle bin")


@router.post("/{log_id}/restore")
async def restore_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("log:list")),
):
    restored = await LogService.restore(db, parse_uuid(log_id))
    if not restored:
        return ResponseModel(code=404, message="Deleted log not found", data=None)
    return ResponseModel(message="Log restored")


@router.delete("/{log_id}/permanent")
async def permanent_delete_log(
    log_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("log:list")),
):
    deleted = await LogService.hard_delete(db, parse_uuid(log_id))
    if not deleted:
        return ResponseModel(code=404, message="Log not found", data=None)
    return ResponseModel(message="Log permanently deleted")

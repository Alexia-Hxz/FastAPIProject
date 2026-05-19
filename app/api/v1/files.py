import os
from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.dependencies import get_current_user, require_permission, parse_uuid
from app.models.user import User
from app.schemas.common import ResponseModel, PageResponse, PageInfo
from app.schemas.file import FileResponse as FileResponseSchema
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post("/upload", response_model=ResponseModel[FileResponseSchema])
async def upload_file(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    _: User = Depends(require_permission("file:upload")),
):
    try:
        file_record = await FileService.upload(db, file, current_user.id)
        return ResponseModel(data=FileResponseSchema.model_validate(file_record))
    except ValueError as e:
        return ResponseModel(code=400, message=str(e), data=None)


@router.get("", response_model=ResponseModel[PageResponse[FileResponseSchema]])
async def list_files(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("file:list")),
):
    files, total = await FileService.get_list(db, page, page_size)
    items = [FileResponseSchema.model_validate(f) for f in files]
    return ResponseModel(data=PageResponse(items=items, pagination=PageInfo(page=page, page_size=page_size, total=total)))


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("file:download")),
):
    file_record = await FileService.get_by_id(db, parse_uuid(file_id))
    if not file_record:
        return ResponseModel(code=404, message="File not found", data=None)
    if not os.path.exists(file_record.storage_path):
        return ResponseModel(code=404, message="File not found on disk", data=None)

    # Update download count
    file_record.download_count += 1
    await db.commit()

    return FileResponse(
        path=file_record.storage_path,
        filename=file_record.original_name,
        media_type=file_record.mime_type or "application/octet-stream",
    )


@router.delete("/{file_id}", response_model=ResponseModel)
async def delete_file(
    file_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission("file:delete")),
):
    file_record = await FileService.get_by_id(db, parse_uuid(file_id))
    if not file_record:
        return ResponseModel(code=404, message="File not found", data=None)
    await FileService.delete(db, file_record)
    return ResponseModel(message="File deleted")

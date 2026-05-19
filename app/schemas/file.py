from app.schemas.common import ORMBase


class FileResponse(ORMBase):
    id: str
    original_name: str
    storage_name: str
    file_size: int
    mime_type: str | None
    file_extension: str | None
    storage_type: str
    download_count: int
    created_at: str

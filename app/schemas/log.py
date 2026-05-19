from pydantic import BaseModel
from app.schemas.common import ORMBase


class LogResponse(ORMBase):
    id: str
    user_id: str | None
    username: str | None
    request_method: str
    request_url: str
    ip_address: str | None
    response_status: int
    duration_ms: int
    module: str | None
    action: str | None
    created_at: str
    deleted_at: str | None = None
    deleted_by: str | None = None


class LogDetailResponse(LogResponse):
    request_params: dict | None = None
    request_body: dict | None = None
    user_agent: str | None = None
    error_message: str | None = None


class LogFilterParams(BaseModel):
    page: int = 1
    page_size: int = 10
    username: str | None = None
    module: str | None = None
    method: str | None = None
    status_code: int | None = None
    start_time: str | None = None
    end_time: str | None = None

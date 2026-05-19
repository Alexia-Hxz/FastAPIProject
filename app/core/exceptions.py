from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_500_INTERNAL_SERVER_ERROR,
)


class AppException(HTTPException):
    def __init__(self, status_code: int, message: str, code: int | None = None):
        self.code = code or status_code
        super().__init__(status_code=status_code, detail=message)


class BadRequestError(AppException):
    def __init__(self, message: str = "Bad request"):
        super().__init__(status_code=HTTP_400_BAD_REQUEST, message=message)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "Not authenticated"):
        super().__init__(status_code=HTTP_401_UNAUTHORIZED, message=message)


class ForbiddenError(AppException):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(status_code=HTTP_403_FORBIDDEN, message=message)


class NotFoundError(AppException):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(status_code=HTTP_404_NOT_FOUND, message=message)


class ConflictError(AppException):
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(status_code=HTTP_409_CONFLICT, message=message)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.detail, "data": None},
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    import traceback
    print(f"\n[ERROR] {request.method} {request.url.path}")
    traceback.print_exc()
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"code": 500, "message": "Internal server error", "data": None},
    )

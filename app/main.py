import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import settings, PROJECT_ROOT as _PROJECT_ROOT
from app.core.database import engine
from app.core.exceptions import AppException, app_exception_handler, general_exception_handler
from app.middleware.cors import setup_cors
from app.middleware.operation_log import OperationLogMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.models.base import Base
from app.api.v1.auth import router as auth_router
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

setup_cors(app)
static_dir = os.path.join(_PROJECT_ROOT, "static")
app.mount("/app", StaticFiles(directory=static_dir, html=True), name="static")
app.add_middleware(RateLimitMiddleware, max_requests=settings.RATE_LIMIT_PER_MINUTE)
app.add_middleware(OperationLogMiddleware)

app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["health"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

from fastapi import APIRouter
from app.api.v1.users import router as users_router
from app.api.v1.roles import router as roles_router
from app.api.v1.menus import router as menus_router
from app.api.v1.logs import router as logs_router
from app.api.v1.files import router as files_router
from app.api.v1.ai import router as ai_router
from app.api.v1.codegen import router as codegen_router

api_router = APIRouter()
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(menus_router)
api_router.include_router(logs_router)
api_router.include_router(files_router)
api_router.include_router(ai_router)
api_router.include_router(codegen_router)

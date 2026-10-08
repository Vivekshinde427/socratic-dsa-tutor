from fastapi import APIRouter

from backend.app.api.v1.auth import router as auth_router
from backend.app.api.v1.health import router as health_router
from backend.app.api.v1.problems import router as problems_router
from backend.app.api.v1.users import router as users_router
from backend.app.api.v1.admin import router as admin_router
from backend.app.api.v1.sessions import router as sessions_router
from backend.app.api.v1.progress import router as progress_router

api_router = APIRouter()

# Root health check endpoint
api_router.include_router(health_router)

# V1 API endpoints
v1_router = APIRouter(prefix="/api/v1")
v1_router.include_router(health_router)
v1_router.include_router(auth_router)
v1_router.include_router(users_router)
v1_router.include_router(problems_router)
v1_router.include_router(admin_router)
v1_router.include_router(sessions_router)
v1_router.include_router(progress_router)

api_router.include_router(v1_router)

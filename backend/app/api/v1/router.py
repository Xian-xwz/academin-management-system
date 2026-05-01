from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.ai import router as ai_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.forum import router as forum_router
from app.api.v1.health import router as health_router
from app.api.v1.openclaw import router as openclaw_router
from app.api.v1.schedule import router as schedule_router
from app.api.v1.students import router as students_router
from app.api.v1.time_plan import router as time_plan_router


api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(admin_router)
api_router.include_router(dashboard_router)
api_router.include_router(students_router)
api_router.include_router(ai_router)
api_router.include_router(openclaw_router)
api_router.include_router(schedule_router)
api_router.include_router(time_plan_router)
api_router.include_router(forum_router)

from fastapi import APIRouter

from app.api import auth, jobs, projects, settings

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(settings.router)
api_router.include_router(jobs.router)

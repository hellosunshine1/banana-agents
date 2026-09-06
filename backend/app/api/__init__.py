from fastapi import APIRouter

from app.api import agent, auth, jobs, pipeline, projects, settings

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(settings.router)
api_router.include_router(jobs.router)
api_router.include_router(pipeline.router)
api_router.include_router(agent.router)

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models import AgentAuditLog, Project, User
from app.schemas import AgentChatRequest, AgentChatResponse, AuditOut
from app.services.agent.service import handle_agent_chat

router = APIRouter(prefix="/projects/{project_id}/agent", tags=["agent"])


async def _owned_project(db: AsyncSession, project_id: int, user: User) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.post("/chat", response_model=AgentChatResponse)
async def agent_chat(
    project_id: int,
    body: AgentChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AgentChatResponse:
    project = await _owned_project(db, project_id, current_user)
    result = await handle_agent_chat(
        db,
        project=project,
        user=current_user,
        message=body.message,
        chapter_number=body.chapter_number,
        guidance=body.guidance,
    )
    return AgentChatResponse(**result)


@router.get("/audits", response_model=list[AuditOut])
async def list_audits(
    project_id: int,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AgentAuditLog]:
    await _owned_project(db, project_id, current_user)
    result = await db.execute(
        select(AgentAuditLog)
        .where(AgentAuditLog.project_id == project_id)
        .order_by(AgentAuditLog.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())

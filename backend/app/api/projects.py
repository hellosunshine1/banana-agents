from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models import GenerationJob, Project, User
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


async def _get_owned_project(db: AsyncSession, project_id: int, user: User) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Project]:
    result = await db.execute(
        select(Project).where(Project.owner_id == current_user.id).order_by(Project.id.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = Project(
        owner_id=current_user.id,
        name=body.name,
        topic=body.topic,
        genre=body.genre,
        num_chapters=body.num_chapters,
        word_number=body.word_number,
        model_routing=body.model_routing,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    return await _get_owned_project(db, project_id, current_user)


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Project:
    project = await _get_owned_project(db, project_id, current_user)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    project = await _get_owned_project(db, project_id, current_user)
    jobs = await db.execute(select(GenerationJob).where(GenerationJob.project_id == project.id))
    for job in jobs.scalars().all():
        await db.delete(job)
    await db.delete(project)
    await db.commit()

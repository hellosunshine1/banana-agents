from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models import GenerationJob, User
from app.schemas import JobOut

router = APIRouter(prefix="/jobs", tags=["jobs"])

CANCELABLE = {"pending", "running"}


async def _get_owned_job(db: AsyncSession, job_id: int, user: User) -> GenerationJob:
    result = await db.execute(
        select(GenerationJob).where(GenerationJob.id == job_id, GenerationJob.user_id == user.id)
    )
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return job


@router.get("/{job_id}", response_model=JobOut)
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationJob:
    return await _get_owned_job(db, job_id, current_user)


@router.post("/{job_id}/cancel", response_model=JobOut)
async def cancel_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerationJob:
    job = await _get_owned_job(db, job_id, current_user)
    if job.status not in CANCELABLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job status '{job.status}' cannot be cancelled",
        )
    job.status = "cancelled"
    await db.commit()
    await db.refresh(job)
    return job

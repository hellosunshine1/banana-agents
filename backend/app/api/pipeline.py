from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_db
from app.models import ChapterBlueprint, ConsistencyReview, Project, User
from app.schemas import (
    BlueprintItem,
    BlueprintListOut,
    BlueprintPut,
    ChapterOut,
    ChapterUpdate,
    ConsistencyReviewOut,
    DraftRequest,
    JobCreated,
    RagHit,
    RagQueryOut,
    RagQueryRequest,
)
from app.services.jobs.runner import create_and_enqueue
from app.services.pipeline import get_or_create_chapter, stream_chapter_draft
from app.services.rag.store import similarity_search

router = APIRouter(prefix="/projects/{project_id}", tags=["pipeline"])


async def _owned_project(db: AsyncSession, project_id: int, user: User) -> Project:
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


def _sse(event: str, data: dict) -> str:
    payload = {"event": event, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/architecture/generate", response_model=JobCreated, status_code=status.HTTP_202_ACCEPTED)
async def generate_architecture(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobCreated:
    project = await _owned_project(db, project_id, current_user)
    job = await create_and_enqueue(
        db, user_id=current_user.id, project_id=project.id, job_type="architecture"
    )
    return JobCreated(job_id=job.id)


@router.post("/blueprint/generate", response_model=JobCreated, status_code=status.HTTP_202_ACCEPTED)
async def generate_blueprint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobCreated:
    project = await _owned_project(db, project_id, current_user)
    job = await create_and_enqueue(
        db, user_id=current_user.id, project_id=project.id, job_type="blueprint"
    )
    return JobCreated(job_id=job.id)


@router.get("/blueprint", response_model=BlueprintListOut)
async def get_blueprint(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlueprintListOut:
    await _owned_project(db, project_id, current_user)
    result = await db.execute(
        select(ChapterBlueprint)
        .where(ChapterBlueprint.project_id == project_id)
        .order_by(ChapterBlueprint.chapter_number.asc())
    )
    rows = result.scalars().all()
    return BlueprintListOut(
        items=[
            BlueprintItem(
                chapter_number=r.chapter_number,
                title=r.title,
                summary=r.summary,
                raw_text=r.raw_text,
            )
            for r in rows
        ]
    )


@router.put("/blueprint", response_model=BlueprintListOut)
async def put_blueprint(
    project_id: int,
    body: BlueprintPut,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> BlueprintListOut:
    await _owned_project(db, project_id, current_user)
    existing = await db.execute(
        select(ChapterBlueprint).where(ChapterBlueprint.project_id == project_id)
    )
    for row in existing.scalars().all():
        await db.delete(row)
    for item in body.items:
        db.add(
            ChapterBlueprint(
                project_id=project_id,
                chapter_number=item.chapter_number,
                title=item.title,
                summary=item.summary,
                raw_text=item.raw_text,
            )
        )
    await db.commit()
    result = await db.execute(
        select(ChapterBlueprint)
        .where(ChapterBlueprint.project_id == project_id)
        .order_by(ChapterBlueprint.chapter_number.asc())
    )
    rows = result.scalars().all()
    return BlueprintListOut(
        items=[
            BlueprintItem(
                chapter_number=r.chapter_number,
                title=r.title,
                summary=r.summary,
                raw_text=r.raw_text,
            )
            for r in rows
        ]
    )


@router.get("/chapters/{chapter_number}", response_model=ChapterOut)
async def get_chapter(
    project_id: int,
    chapter_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChapterOut:
    await _owned_project(db, project_id, current_user)
    chapter = await get_or_create_chapter(db, project_id, chapter_number)
    return ChapterOut.model_validate(chapter)


@router.put("/chapters/{chapter_number}", response_model=ChapterOut)
async def put_chapter(
    project_id: int,
    chapter_number: int,
    body: ChapterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChapterOut:
    await _owned_project(db, project_id, current_user)
    chapter = await get_or_create_chapter(db, project_id, chapter_number)
    chapter.content = body.content
    chapter.status = "draft" if body.content.strip() else "empty"
    await db.commit()
    await db.refresh(chapter)
    return ChapterOut.model_validate(chapter)


@router.post("/chapters/{chapter_number}/draft")
async def draft_chapter(
    project_id: int,
    chapter_number: int,
    request: Request,
    body: DraftRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    project = await _owned_project(db, project_id, current_user)
    guidance = (body.guidance if body else "") or ""
    chapter = await get_or_create_chapter(db, project_id, chapter_number)
    chapter.status = "drafting"
    await db.commit()

    async def event_gen() -> AsyncIterator[str]:
        collected: list[str] = []
        try:
            yield _sse("meta", {"project_id": project_id, "chapter_number": chapter_number})
            async for token in stream_chapter_draft(db, project, chapter_number, guidance):
                if await request.is_disconnected():
                    break
                collected.append(token)
                yield _sse("token", {"text": token})
            text = "".join(collected)
            ch = await get_or_create_chapter(db, project_id, chapter_number)
            if text.strip():
                ch.content = text
                ch.status = "draft"
                await db.commit()
            yield _sse("usage", {"chars": len(text)})
            yield _sse("done", {"chapter_number": chapter_number, "saved": bool(text.strip())})
        except Exception as exc:
            text = "".join(collected)
            try:
                ch = await get_or_create_chapter(db, project_id, chapter_number)
                if text.strip():
                    ch.content = text
                    ch.status = "draft"
                    await db.commit()
            except Exception:
                await db.rollback()
            yield _sse("error", {"message": str(exc)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.post(
    "/chapters/{chapter_number}/finalize",
    response_model=JobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def finalize_chapter(
    project_id: int,
    chapter_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobCreated:
    project = await _owned_project(db, project_id, current_user)
    chapter = await get_or_create_chapter(db, project_id, chapter_number)
    if not chapter.content.strip():
        raise HTTPException(status_code=400, detail="Chapter content is empty")
    job = await create_and_enqueue(
        db,
        user_id=current_user.id,
        project_id=project.id,
        job_type="finalize",
        result_ref=f"chapter:{chapter_number}",
    )
    return JobCreated(job_id=job.id)


@router.post(
    "/chapters/{chapter_number}/consistency-check",
    response_model=JobCreated,
    status_code=status.HTTP_202_ACCEPTED,
)
async def consistency_check(
    project_id: int,
    chapter_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> JobCreated:
    project = await _owned_project(db, project_id, current_user)
    chapter = await get_or_create_chapter(db, project_id, chapter_number)
    if not chapter.content.strip():
        raise HTTPException(status_code=400, detail="Chapter content is empty")
    job = await create_and_enqueue(
        db,
        user_id=current_user.id,
        project_id=project.id,
        job_type="consistency",
        result_ref=f"chapter:{chapter_number}",
    )
    return JobCreated(job_id=job.id)


@router.get("/chapters/{chapter_number}/reviews", response_model=list[ConsistencyReviewOut])
async def list_reviews(
    project_id: int,
    chapter_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ConsistencyReview]:
    await _owned_project(db, project_id, current_user)
    result = await db.execute(
        select(ConsistencyReview)
        .where(
            ConsistencyReview.project_id == project_id,
            ConsistencyReview.chapter_number == chapter_number,
        )
        .order_by(ConsistencyReview.id.desc())
    )
    return list(result.scalars().all())


@router.post("/rag/query", response_model=RagQueryOut)
async def rag_query(
    project_id: int,
    body: RagQueryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RagQueryOut:
    await _owned_project(db, project_id, current_user)
    hits = await similarity_search(
        db, project_id=project_id, query=body.query, top_k=body.top_k
    )
    return RagQueryOut(hits=[RagHit(**h) for h in hits])

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Chapter, ChapterBlueprint, Project
from app.services.jobs.runner import create_and_enqueue
from app.services.pipeline import get_or_create_chapter
from app.services.rag.store import similarity_search

WHITELIST = {
    "tool_generate_architecture",
    "tool_generate_blueprint",
    "tool_generate_draft",
    "tool_finalize_chapter",
    "tool_consistency_check",
    "tool_get_artifact",
    "tool_rag_query",
}


class ToolError(Exception):
    def __init__(self, message: str, *, status: str = "rejected"):
        super().__init__(message)
        self.status = status


def _ensure_project_id(path_project_id: int, args: dict[str, Any]) -> None:
    if "project_id" in args and args["project_id"] is not None:
        if int(args["project_id"]) != path_project_id:
            raise ToolError("Cross-project project_id is not allowed")


async def execute_tool(
    db: AsyncSession,
    *,
    tool_name: str,
    path_project_id: int,
    user_id: int,
    args: dict[str, Any],
) -> dict[str, Any]:
    if tool_name not in WHITELIST:
        raise ToolError(f"Tool not in whitelist: {tool_name}")

    _ensure_project_id(path_project_id, args)
    project_id = path_project_id

    if tool_name == "tool_generate_architecture":
        job = await create_and_enqueue(
            db, user_id=user_id, project_id=project_id, job_type="architecture"
        )
        return {"job_id": job.id, "message": "Architecture job created"}

    if tool_name == "tool_generate_blueprint":
        job = await create_and_enqueue(
            db, user_id=user_id, project_id=project_id, job_type="blueprint"
        )
        return {"job_id": job.id, "message": "Blueprint job created"}

    if tool_name == "tool_generate_draft":
        chapter_number = int(args.get("chapter_number") or 0)
        if chapter_number <= 0:
            raise ToolError("chapter_number is required for draft")
        guidance = str(args.get("guidance") or "")
        return {
            "sse_endpoint": f"/api/projects/{project_id}/chapters/{chapter_number}/draft",
            "chapter_number": chapter_number,
            "guidance": guidance,
            "message": "Call SSE endpoint to stream draft; tokens are not returned here",
        }

    if tool_name == "tool_finalize_chapter":
        chapter_number = int(args.get("chapter_number") or 0)
        if chapter_number <= 0:
            raise ToolError("chapter_number is required for finalize")
        chapter = await get_or_create_chapter(db, project_id, chapter_number)
        if not chapter.content.strip():
            raise ToolError("Chapter content is empty", status="error")
        job = await create_and_enqueue(
            db,
            user_id=user_id,
            project_id=project_id,
            job_type="finalize",
            result_ref=f"chapter:{chapter_number}",
        )
        return {"job_id": job.id, "message": "Finalize job created"}

    if tool_name == "tool_consistency_check":
        chapter_number = int(args.get("chapter_number") or 0)
        if chapter_number <= 0:
            raise ToolError("chapter_number is required for consistency check")
        chapter = await get_or_create_chapter(db, project_id, chapter_number)
        if not chapter.content.strip():
            raise ToolError("Chapter content is empty", status="error")
        job = await create_and_enqueue(
            db,
            user_id=user_id,
            project_id=project_id,
            job_type="consistency",
            result_ref=f"chapter:{chapter_number}",
        )
        return {"job_id": job.id, "message": "Consistency check job created"}

    if tool_name == "tool_get_artifact":
        artifact_type = str(args.get("artifact_type") or "")
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one()
        if artifact_type == "architecture":
            return {"artifact_type": artifact_type, "content": project.architecture}
        if artifact_type == "character_state":
            return {"artifact_type": artifact_type, "content": project.character_state}
        if artifact_type == "global_summary":
            return {"artifact_type": artifact_type, "content": project.global_summary}
        if artifact_type == "blueprint":
            rows = await db.execute(
                select(ChapterBlueprint)
                .where(ChapterBlueprint.project_id == project_id)
                .order_by(ChapterBlueprint.chapter_number.asc())
            )
            items = [
                {
                    "chapter_number": r.chapter_number,
                    "title": r.title,
                    "summary": r.summary,
                }
                for r in rows.scalars().all()
            ]
            return {"artifact_type": artifact_type, "items": items}
        if artifact_type == "chapter":
            chapter_number = int(args.get("chapter_number") or 0)
            if chapter_number <= 0:
                raise ToolError("chapter_number is required for chapter artifact")
            ch = await db.execute(
                select(Chapter).where(
                    Chapter.project_id == project_id,
                    Chapter.chapter_number == chapter_number,
                )
            )
            chapter = ch.scalar_one_or_none()
            return {
                "artifact_type": artifact_type,
                "chapter_number": chapter_number,
                "content": chapter.content if chapter else "",
                "status": chapter.status if chapter else "empty",
            }
        raise ToolError(f"Unknown artifact_type: {artifact_type}")

    if tool_name == "tool_rag_query":
        query = str(args.get("query") or "").strip()
        if not query:
            raise ToolError("query is required")
        top_k = args.get("top_k")
        hits = await similarity_search(
            db,
            project_id=project_id,
            query=query,
            top_k=int(top_k) if top_k else None,
        )
        return {"hits": hits, "message": f"Found {len(hits)} hits"}

    raise ToolError(f"Unhandled tool: {tool_name}")

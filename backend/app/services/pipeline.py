from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Chapter, ChapterBlueprint, Project
from app.services.dify.client import run_workflow_streaming
from app.services.dify.fallback import chat_stream, use_dify
from app.services.rag.store import format_rag_context
from app.services.routing import get_llm_preset, load_app_settings, resolve_choose_configs


async def get_or_create_chapter(
    db: AsyncSession, project_id: int, chapter_number: int
) -> Chapter:
    result = await db.execute(
        select(Chapter).where(
            Chapter.project_id == project_id,
            Chapter.chapter_number == chapter_number,
        )
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        chapter = Chapter(
            project_id=project_id,
            chapter_number=chapter_number,
            content="",
            status="empty",
        )
        db.add(chapter)
        await db.commit()
        await db.refresh(chapter)
    return chapter


async def build_draft_context(
    db: AsyncSession,
    project: Project,
    chapter_number: int,
    guidance: str = "",
) -> str:
    bp_result = await db.execute(
        select(ChapterBlueprint).where(
            ChapterBlueprint.project_id == project.id,
            ChapterBlueprint.chapter_number == chapter_number,
        )
    )
    bp = bp_result.scalar_one_or_none()
    rag_query = bp.summary if bp and bp.summary else f"{project.topic} 第{chapter_number}章"
    try:
        rag_ctx = await format_rag_context(db, project.id, rag_query)
    except Exception:
        rag_ctx = ""

    parts = [
        f"【小说设定】\n{project.architecture}",
        f"【角色状态】\n{project.character_state}",
        f"【全局摘要】\n{project.global_summary}",
    ]
    if bp:
        parts.append(f"【本章蓝图】\n标题：{bp.title}\n概要：{bp.summary}\n{bp.raw_text}")
    if rag_ctx:
        parts.append(f"【相关定稿片段】\n{rag_ctx}")
    if guidance:
        parts.append(f"【本章指导】\n{guidance}")
    parts.append(
        f"请撰写第 {chapter_number} 章正文，目标约 {project.word_number} 字，保持人设与前文一致。"
    )
    return "\n\n".join(parts)


async def stream_chapter_draft(
    db: AsyncSession,
    project: Project,
    chapter_number: int,
    guidance: str = "",
) -> AsyncIterator[str]:
    context = await build_draft_context(db, project, chapter_number, guidance)
    settings = get_settings()
    wf = settings.dify_wf_chapter_draft
    if use_dify(wf):
        async for token in run_workflow_streaming(
            wf,
            {
                "chapter_number": chapter_number,
                "guidance": guidance,
                "context": context,
                "architecture": project.architecture,
                "character_state": project.character_state,
                "global_summary": project.global_summary,
                "word_number": project.word_number,
            },
        ):
            yield token
        return

    settings_row = await load_app_settings(db)
    choose = resolve_choose_configs(project, settings_row)
    preset = get_llm_preset(settings_row, choose.get("prompt_draft_llm", ""))
    async for token in chat_stream(preset, context, system="你是专业网文作者，只输出章节正文。"):
        yield token

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import AsyncSessionLocal
from app.models import ChapterBlueprint, GenerationJob, Project
from app.services.dify.client import extract_text_output, run_workflow_blocking
from app.services.dify.fallback import chat_complete, use_dify
from app.services.rag.store import upsert_chapter_chunks
from app.services.routing import get_llm_preset, load_app_settings, resolve_choose_configs

logger = logging.getLogger(__name__)

_semaphore: asyncio.Semaphore | None = None
_cancel_flags: dict[int, asyncio.Event] = {}


def get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(get_settings().job_max_concurrency)
    return _semaphore


def request_cancel(job_id: int) -> None:
    event = _cancel_flags.get(job_id)
    if event:
        event.set()


async def _is_cancelled(db: AsyncSession, job_id: int) -> bool:
    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
    job = result.scalar_one_or_none()
    return job is None or job.status == "cancelled"


async def _set_job(
    db: AsyncSession,
    job: GenerationJob,
    *,
    status: str | None = None,
    progress: int | None = None,
    error: str | None = None,
    result_ref: str | None = None,
) -> None:
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error = error
    if result_ref is not None:
        job.result_ref = result_ref
    await db.commit()
    await db.refresh(job)


def _parse_architecture_payload(text: str) -> tuple[str, str]:
    """Return (architecture, character_state). Try JSON else whole text."""
    text = text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            arch = str(data.get("architecture") or data.get("setting") or data.get("text") or text)
            chars = str(data.get("character_state") or data.get("characters") or "")
            return arch, chars
    except json.JSONDecodeError:
        pass
    # split markers
    if "【角色状态】" in text:
        parts = text.split("【角色状态】", 1)
        return parts[0].replace("【小说设定】", "").strip(), parts[1].strip()
    return text, ""


def _parse_blueprint_items(text: str, num_chapters: int) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    try:
        data = json.loads(text)
        if isinstance(data, list):
            for i, row in enumerate(data, start=1):
                if isinstance(row, dict):
                    items.append(
                        {
                            "chapter_number": int(row.get("chapter_number") or i),
                            "title": str(row.get("title") or f"第{i}章"),
                            "summary": str(row.get("summary") or row.get("outline") or ""),
                            "raw_text": str(row.get("raw_text") or json.dumps(row, ensure_ascii=False)),
                        }
                    )
            if items:
                return items[:num_chapters] if num_chapters > 0 else items
        if isinstance(data, dict) and "chapters" in data:
            return _parse_blueprint_items(json.dumps(data["chapters"], ensure_ascii=False), num_chapters)
    except json.JSONDecodeError:
        pass

    # fallback: split by chapter headings
    pattern = re.compile(r"(?:第\s*(\d+)\s*章|[Cc]hapter\s*(\d+))[：:\s]*(.*)")
    lines = text.splitlines()
    current: dict[str, Any] | None = None
    for line in lines:
        m = pattern.search(line.strip())
        if m:
            if current:
                items.append(current)
            num = int(m.group(1) or m.group(2))
            title = (m.group(3) or f"第{num}章").strip() or f"第{num}章"
            current = {"chapter_number": num, "title": title, "summary": "", "raw_text": line}
        elif current is not None:
            current["summary"] = (current["summary"] + "\n" + line).strip()
            current["raw_text"] = (current["raw_text"] + "\n" + line).strip()
    if current:
        items.append(current)
    if not items and num_chapters > 0:
        for i in range(1, num_chapters + 1):
            items.append(
                {
                    "chapter_number": i,
                    "title": f"第{i}章",
                    "summary": text if i == 1 else "",
                    "raw_text": text if i == 1 else "",
                }
            )
    return items


async def _generate_architecture_text(db: AsyncSession, project: Project) -> tuple[str, str]:
    settings_row = await load_app_settings(db)
    choose = resolve_choose_configs(project, settings_row)
    from app.config import get_settings as gs

    wf = gs().dify_wf_architecture
    prompt = (
        f"请为小说生成完整设定与初始角色状态。\n"
        f"主题：{project.topic}\n类型：{project.genre}\n"
        f"总章数：{project.num_chapters}\n每章字数：{project.word_number}\n"
        f"请尽量输出 JSON：{{\"architecture\": \"...\", \"character_state\": \"...\"}}"
    )
    if use_dify(wf):
        result = await run_workflow_blocking(
            wf,
            {
                "topic": project.topic,
                "genre": project.genre,
                "num_chapters": project.num_chapters,
                "word_number": project.word_number,
                "name": project.name,
            },
        )
        text = extract_text_output(result)
    else:
        preset = get_llm_preset(settings_row, choose.get("architecture_llm", ""))
        text = await chat_complete(preset, prompt, system="你是资深网文策划编辑。")
    return _parse_architecture_payload(text)


async def _generate_blueprint_text(db: AsyncSession, project: Project) -> str:
    settings_row = await load_app_settings(db)
    choose = resolve_choose_configs(project, settings_row)
    from app.config import get_settings as gs

    wf = gs().dify_wf_blueprint
    prompt = (
        f"根据以下小说设定，生成共 {project.num_chapters} 章的目录蓝图。\n"
        f"设定：\n{project.architecture}\n\n"
        f"请输出 JSON 数组，每项含 chapter_number, title, summary。"
    )
    if use_dify(wf):
        result = await run_workflow_blocking(
            wf,
            {
                "architecture": project.architecture,
                "num_chapters": project.num_chapters,
                "topic": project.topic,
                "genre": project.genre,
            },
        )
        return extract_text_output(result)
    preset = get_llm_preset(settings_row, choose.get("chapter_outline_llm", ""))
    return await chat_complete(preset, prompt, system="你是资深网文大纲编辑。")


async def _run_consistency_review(
    db: AsyncSession, project: Project, chapter_number: int, content: str
) -> tuple[dict[str, Any], str]:
    settings_row = await load_app_settings(db)
    choose = resolve_choose_configs(project, settings_row)
    from app.config import get_settings as gs

    wf = gs().dify_wf_consistency_review
    prompt = (
        "请审校本章正文与小说设定/角色状态/全局摘要是否存在矛盾。\n"
        f"设定：\n{project.architecture}\n\n"
        f"角色状态：\n{project.character_state}\n\n"
        f"全局摘要：\n{project.global_summary}\n\n"
        f"第{chapter_number}章正文：\n{content}\n\n"
        '请只输出 JSON：{"summary":"...","conflicts":[{"type":"...","severity":"...","detail":"...","locations":[]}]}'
    )
    if use_dify(wf):
        result = await run_workflow_blocking(
            wf,
            {
                "chapter_number": chapter_number,
                "content": content,
                "architecture": project.architecture,
                "character_state": project.character_state,
                "global_summary": project.global_summary,
            },
        )
        text = extract_text_output(result)
    else:
        preset = get_llm_preset(settings_row, choose.get("consistency_review_llm", ""))
        text = await chat_complete(preset, prompt, system="你是严谨的小说一致性审校员，只输出 JSON。")

    conflicts: dict[str, Any]
    try:
        data = json.loads(text.strip().strip("`").removeprefix("json").strip())
        if isinstance(data, dict):
            if "conflicts" not in data:
                data = {"conflicts": [data] if data else [], "summary": ""}
            conflicts = data
        elif isinstance(data, list):
            conflicts = {"conflicts": data, "summary": ""}
        else:
            conflicts = {"conflicts": [], "summary": str(data)}
    except json.JSONDecodeError:
        conflicts = {
            "summary": "模型未返回合法 JSON，原始文本见 raw",
            "conflicts": [
                {
                    "type": "parse_error",
                    "severity": "medium",
                    "detail": text[:2000],
                    "locations": [],
                }
            ],
        }
    return conflicts, text


async def _finalize_summary(
    db: AsyncSession, project: Project, chapter_number: int, content: str
) -> tuple[str, str]:
    settings_row = await load_app_settings(db)
    choose = resolve_choose_configs(project, settings_row)
    from app.config import get_settings as gs

    wf = gs().dify_wf_finalize_summary
    prompt = (
        f"请基于本章正文更新全局摘要与角色状态。\n"
        f"旧全局摘要：\n{project.global_summary}\n\n"
        f"旧角色状态：\n{project.character_state}\n\n"
        f"第{chapter_number}章正文：\n{content}\n\n"
        f"请输出 JSON：{{\"global_summary\": \"...\", \"character_state\": \"...\"}}"
    )
    if use_dify(wf):
        result = await run_workflow_blocking(
            wf,
            {
                "chapter_number": chapter_number,
                "content": content,
                "global_summary": project.global_summary,
                "character_state": project.character_state,
                "architecture": project.architecture,
            },
        )
        text = extract_text_output(result)
    else:
        preset = get_llm_preset(settings_row, choose.get("final_chapter_llm", ""))
        text = await chat_complete(preset, prompt, system="你是严谨的长篇连载状态维护编辑。")

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return (
                str(data.get("global_summary") or project.global_summary),
                str(data.get("character_state") or project.character_state),
            )
    except json.JSONDecodeError:
        pass
    return text, project.character_state


async def run_job(job_id: int) -> None:
    cancel_event = asyncio.Event()
    _cancel_flags[job_id] = cancel_event
    settings = get_settings()
    try:
        async with get_semaphore():
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
                job = result.scalar_one_or_none()
                if job is None or job.status == "cancelled":
                    return
                await _set_job(db, job, status="running", progress=5)

                proj_result = await db.execute(select(Project).where(Project.id == job.project_id))
                project = proj_result.scalar_one()

                try:
                    if await _is_cancelled(db, job_id) or cancel_event.is_set():
                        return

                    if job.type == "architecture":
                        await _set_job(db, job, progress=20)
                        arch, chars = await asyncio.wait_for(
                            _generate_architecture_text(db, project),
                            timeout=settings.job_timeout_sec,
                        )
                        if await _is_cancelled(db, job_id):
                            return
                        project.architecture = arch
                        if chars:
                            project.character_state = chars
                        await db.commit()
                        await _set_job(db, job, status="succeeded", progress=100, result_ref="architecture")

                    elif job.type == "blueprint":
                        await _set_job(db, job, progress=20)
                        text = await asyncio.wait_for(
                            _generate_blueprint_text(db, project),
                            timeout=settings.job_timeout_sec,
                        )
                        if await _is_cancelled(db, job_id):
                            return
                        items = _parse_blueprint_items(text, project.num_chapters)
                        existing = await db.execute(
                            select(ChapterBlueprint).where(ChapterBlueprint.project_id == project.id)
                        )
                        for row in existing.scalars().all():
                            await db.delete(row)
                        for item in items:
                            db.add(
                                ChapterBlueprint(
                                    project_id=project.id,
                                    chapter_number=item["chapter_number"],
                                    title=item["title"],
                                    summary=item["summary"],
                                    raw_text=item["raw_text"],
                                )
                            )
                        await db.commit()
                        await _set_job(db, job, status="succeeded", progress=100, result_ref="blueprint")

                    elif job.type == "finalize":
                        ref = job.result_ref or ""
                        if ref.startswith("chapter:"):
                            chapter_number = int(ref.split(":", 1)[1])
                        else:
                            chapter_number = int(ref or "0")
                        if chapter_number <= 0:
                            raise ValueError("finalize job missing chapter_number in result_ref")
                        from app.models import Chapter

                        ch_result = await db.execute(
                            select(Chapter).where(
                                Chapter.project_id == project.id,
                                Chapter.chapter_number == chapter_number,
                            )
                        )
                        chapter = ch_result.scalar_one_or_none()
                        if chapter is None or not chapter.content.strip():
                            raise ValueError("Chapter content is empty")
                        await _set_job(db, job, progress=30)
                        summary, chars = await asyncio.wait_for(
                            _finalize_summary(db, project, chapter_number, chapter.content),
                            timeout=settings.job_timeout_sec,
                        )
                        if await _is_cancelled(db, job_id):
                            return
                        project.global_summary = summary
                        project.character_state = chars
                        chapter.status = "finalized"
                        await db.commit()
                        await _set_job(db, job, progress=70)
                        await upsert_chapter_chunks(
                            db,
                            project_id=project.id,
                            chapter_number=chapter_number,
                            content=chapter.content,
                        )
                        await _set_job(
                            db,
                            job,
                            status="succeeded",
                            progress=100,
                            result_ref=f"chapter:{chapter_number}",
                        )
                    elif job.type == "consistency":
                        ref = job.result_ref or ""
                        if ref.startswith("chapter:"):
                            chapter_number = int(ref.split(":", 1)[1])
                        else:
                            chapter_number = int(ref or "0")
                        if chapter_number <= 0:
                            raise ValueError("consistency job missing chapter_number")
                        from app.models import Chapter, ConsistencyReview

                        ch_result = await db.execute(
                            select(Chapter).where(
                                Chapter.project_id == project.id,
                                Chapter.chapter_number == chapter_number,
                            )
                        )
                        chapter = ch_result.scalar_one_or_none()
                        if chapter is None or not chapter.content.strip():
                            raise ValueError("Chapter content is empty")
                        await _set_job(db, job, progress=30)
                        conflicts, raw = await asyncio.wait_for(
                            _run_consistency_review(db, project, chapter_number, chapter.content),
                            timeout=settings.job_timeout_sec,
                        )
                        if await _is_cancelled(db, job_id):
                            return
                        db.add(
                            ConsistencyReview(
                                project_id=project.id,
                                chapter_number=chapter_number,
                                job_id=job.id,
                                conflicts=conflicts,
                                raw_text=raw[:20000],
                            )
                        )
                        await db.commit()
                        await _set_job(
                            db,
                            job,
                            status="succeeded",
                            progress=100,
                            result_ref=f"chapter:{chapter_number}",
                        )
                    else:
                        raise ValueError(f"Unknown job type: {job.type}")
                except Exception as exc:
                    logger.exception("Job %s failed", job_id)
                    await db.rollback()
                    result = await db.execute(select(GenerationJob).where(GenerationJob.id == job_id))
                    job = result.scalar_one_or_none()
                    if job and job.status != "cancelled":
                        await _set_job(db, job, status="failed", error=str(exc)[:2000])
    finally:
        _cancel_flags.pop(job_id, None)


async def create_and_enqueue(
    db: AsyncSession,
    *,
    user_id: int,
    project_id: int,
    job_type: str,
    result_ref: str | None = None,
) -> GenerationJob:
    job = GenerationJob(
        project_id=project_id,
        user_id=user_id,
        type=job_type,
        status="pending",
        progress=0,
        result_ref=result_ref,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    asyncio.create_task(run_job(job.id))
    return job

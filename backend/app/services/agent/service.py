from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, User
from app.services.agent.audit import write_audit
from app.services.agent.intents import (
    INTENT_TO_TOOL,
    classify_intent_with_llm,
    extract_chapter_number,
    extract_rag_query,
)
from app.services.agent.tools import ToolError, execute_tool
from app.services.routing import get_llm_preset, load_app_settings, resolve_choose_configs


async def handle_agent_chat(
    db: AsyncSession,
    *,
    project: Project,
    user: User,
    message: str,
    chapter_number: int | None = None,
    guidance: str | None = None,
) -> dict[str, Any]:
    settings_row = await load_app_settings(db)
    choose = resolve_choose_configs(project, settings_row)
    try:
        preset = get_llm_preset(settings_row, choose.get("consistency_review_llm", ""))
    except Exception:
        preset = None

    intent = await classify_intent_with_llm(message, preset)

    if intent == "edit_artifact":
        resp = {
            "intent": "clarify",
            "tool": None,
            "job_id": None,
            "sse_endpoint": None,
            "message": "M3 Agent 不直接改写制品，请在工作台设定/目录/章节面板中编辑。",
            "data": None,
        }
        await write_audit(
            db,
            project_id=project.id,
            user_id=user.id,
            user_message=message,
            intent="edit_artifact",
            tool_name=None,
            tool_args=None,
            status="ok",
            result_summary=resp["message"],
        )
        return resp

    if intent in {"clarify", "reject"}:
        resp = {
            "intent": intent,
            "tool": None,
            "job_id": None,
            "sse_endpoint": None,
            "message": "请说明要执行的操作：生成设定/目录/草稿、定稿、审校或检索。",
            "data": None,
        }
        await write_audit(
            db,
            project_id=project.id,
            user_id=user.id,
            user_message=message,
            intent=intent,
            tool_name=None,
            tool_args=None,
            status="ok",
            result_summary=resp["message"],
        )
        return resp

    tool_name = INTENT_TO_TOOL.get(intent)
    if not tool_name:
        await write_audit(
            db,
            project_id=project.id,
            user_id=user.id,
            user_message=message,
            intent=intent,
            tool_name=None,
            tool_args=None,
            status="rejected",
            result_summary="No tool mapped for intent",
        )
        return {
            "intent": "reject",
            "tool": None,
            "job_id": None,
            "sse_endpoint": None,
            "message": "不支持的意图",
            "data": None,
        }

    chap = chapter_number or extract_chapter_number(message)
    args: dict[str, Any] = {"project_id": project.id}
    if chap:
        args["chapter_number"] = chap
    if guidance:
        args["guidance"] = guidance
    if intent == "rag_query":
        args["query"] = extract_rag_query(message)
    if intent == "generate_draft" and "chapter_number" not in args:
        args["chapter_number"] = 1

    try:
        data = await execute_tool(
            db,
            tool_name=tool_name,
            path_project_id=project.id,
            user_id=user.id,
            args=args,
        )
        summary = data.get("message") or tool_name
        await write_audit(
            db,
            project_id=project.id,
            user_id=user.id,
            user_message=message,
            intent=intent,
            tool_name=tool_name,
            tool_args=args,
            status="ok",
            result_summary=str(summary),
        )
        return {
            "intent": intent,
            "tool": tool_name,
            "job_id": data.get("job_id"),
            "sse_endpoint": data.get("sse_endpoint"),
            "message": data.get("message") or "ok",
            "data": data,
        }
    except ToolError as exc:
        await write_audit(
            db,
            project_id=project.id,
            user_id=user.id,
            user_message=message,
            intent=intent,
            tool_name=tool_name,
            tool_args=args,
            status=exc.status,
            result_summary=str(exc),
        )
        return {
            "intent": "reject" if exc.status == "rejected" else intent,
            "tool": tool_name,
            "job_id": None,
            "sse_endpoint": None,
            "message": str(exc),
            "data": None,
        }

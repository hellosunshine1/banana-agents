from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentAuditLog


async def write_audit(
    db: AsyncSession,
    *,
    project_id: int,
    user_id: int,
    user_message: str,
    intent: str,
    tool_name: str | None,
    tool_args: dict[str, Any] | None,
    status: str,
    result_summary: str,
) -> AgentAuditLog:
    row = AgentAuditLog(
        project_id=project_id,
        user_id=user_id,
        user_message=user_message[:4000],
        intent=intent,
        tool_name=tool_name,
        tool_args=tool_args,
        status=status,
        result_summary=result_summary[:4000],
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row

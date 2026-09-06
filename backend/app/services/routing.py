from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AppSettings, Project
from app.services.settings_defaults import default_app_settings_payload

TASK_KEYS = (
    "architecture_llm",
    "chapter_outline_llm",
    "prompt_draft_llm",
    "final_chapter_llm",
    "consistency_review_llm",
)


async def load_app_settings(db: AsyncSession) -> AppSettings:
    result = await db.execute(select(AppSettings).order_by(AppSettings.id.asc()).limit(1))
    row = result.scalar_one_or_none()
    if row is not None:
        return row
    payload = default_app_settings_payload()
    row = AppSettings(**payload)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


def resolve_choose_configs(project: Project, settings: AppSettings) -> dict[str, str]:
    base = dict(settings.choose_configs or {})
    override = project.model_routing or {}
    if isinstance(override, dict):
        for key in TASK_KEYS:
            if key in override and override[key]:
                base[key] = str(override[key])
    return base


def get_llm_preset(settings: AppSettings, preset_name: str) -> dict[str, Any]:
    configs = settings.llm_configs or {}
    if preset_name in configs:
        return dict(configs[preset_name])
    if configs:
        return dict(next(iter(configs.values())))
    raise ValueError(f"LLM preset not found: {preset_name}")


def get_embedding_preset(settings: AppSettings) -> dict[str, Any]:
    configs = settings.embedding_configs or {}
    if not configs:
        raise ValueError("No embedding_configs configured")
    # Prefer OpenAI-named preset if present
    if "OpenAI" in configs:
        return dict(configs["OpenAI"])
    return dict(next(iter(configs.values())))

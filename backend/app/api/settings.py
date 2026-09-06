from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_admin_user, get_current_user
from app.db import get_db
from app.models import AppSettings, User
from app.schemas import SettingsOut, SettingsUpdate
from app.services.settings_defaults import default_app_settings_payload

router = APIRouter(prefix="/settings", tags=["settings"])


async def _get_or_create_settings(db: AsyncSession) -> AppSettings:
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


@router.get("", response_model=SettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> AppSettings:
    return await _get_or_create_settings(db)


@router.put("", response_model=SettingsOut)
async def put_settings(
    body: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(get_admin_user),
) -> AppSettings:
    row = await _get_or_create_settings(db)
    row.llm_configs = body.llm_configs
    row.embedding_configs = body.embedding_configs
    row.choose_configs = body.choose_configs
    await db.commit()
    await db.refresh(row)
    return row

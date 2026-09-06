"""Seed admin user, default settings, sample project and pending job."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

# Allow `python -m scripts.seed` from backend/
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db import AsyncSessionLocal
from app.models import AppSettings, GenerationJob, Project, User
from app.services.auth import hash_password
from app.services.settings_defaults import default_app_settings_payload


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.username == "admin"))
        admin = result.scalar_one_or_none()
        if admin is None:
            admin = User(
                username="admin",
                password_hash=hash_password("123456"),
                is_active=True,
                is_admin=True,
            )
            db.add(admin)
            await db.flush()
            print(f"Created admin user id={admin.id}")
        else:
            print(f"Admin already exists id={admin.id}")

        settings_result = await db.execute(select(AppSettings).order_by(AppSettings.id.asc()).limit(1))
        settings = settings_result.scalar_one_or_none()
        if settings is None:
            payload = default_app_settings_payload()
            settings = AppSettings(**payload)
            db.add(settings)
            print("Created default app_settings")
        else:
            print(f"app_settings already exists id={settings.id}")

        project_result = await db.execute(
            select(Project).where(Project.owner_id == admin.id, Project.name == "示例项目")
        )
        project = project_result.scalar_one_or_none()
        if project is None:
            project = Project(
                owner_id=admin.id,
                name="示例项目",
                topic="废土世界的 AI 叛乱",
                genre="科幻",
                num_chapters=10,
                word_number=3000,
            )
            db.add(project)
            await db.flush()
            print(f"Created sample project id={project.id}")
        else:
            print(f"Sample project already exists id={project.id}")

        job_result = await db.execute(
            select(GenerationJob).where(
                GenerationJob.project_id == project.id,
                GenerationJob.type == "architecture",
                GenerationJob.status == "pending",
            )
        )
        job = job_result.scalar_one_or_none()
        if job is None:
            job = GenerationJob(
                project_id=project.id,
                user_id=admin.id,
                type="architecture",
                status="pending",
                progress=0,
            )
            db.add(job)
            await db.flush()
            print(f"Created sample job id={job.id}")
        else:
            print(f"Sample pending job already exists id={job.id}")

        await db.commit()
        print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(seed())

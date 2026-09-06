#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import asyncio
import os
import sys
import time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

url = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://banana:banana@db:5432/banana",
)
deadline = time.time() + 60
last_err: Exception | None = None

async def ping() -> None:
    engine = create_async_engine(url, pool_pre_ping=True)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    finally:
        await engine.dispose()

while time.time() < deadline:
    try:
        asyncio.run(ping())
        print("Database is ready.")
        sys.exit(0)
    except Exception as exc:  # noqa: BLE001
        last_err = exc
        time.sleep(1)

print(f"Database not ready after 60s: {last_err}", file=sys.stderr)
sys.exit(1)
PY

echo "Running migrations..."
alembic upgrade head

echo "Seeding..."
python -m scripts.seed

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

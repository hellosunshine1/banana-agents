from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI
from sqlalchemy import delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import ChapterChunk
from app.services.routing import get_embedding_preset, load_app_settings


def split_chunks(text: str, max_length: int = 500, overlap: int = 50) -> list[str]:
    text = (text or "").strip()
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_length, n)
        chunks.append(text[start:end])
        if end >= n:
            break
        start = max(0, end - overlap)
    return chunks


async def _embed_texts(preset: dict[str, Any], texts: list[str]) -> list[list[float]]:
    api_key = (preset.get("api_key") or "").strip()
    if not api_key:
        raise ValueError("Embedding api_key is empty; configure it in Settings")
    base_url = (preset.get("base_url") or "https://api.openai.com/v1").rstrip("/")
    model = preset.get("model_name") or "text-embedding-3-small"
    client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=float(preset.get("timeout") or 600))
    resp = await client.embeddings.create(model=model, input=texts)
    dim = get_settings().embedding_dim
    vectors: list[list[float]] = []
    for item in resp.data:
        vec = list(item.embedding)
        if len(vec) != dim:
            # pad or truncate to fixed dim for pgvector column
            if len(vec) < dim:
                vec = vec + [0.0] * (dim - len(vec))
            else:
                vec = vec[:dim]
        vectors.append(vec)
    return vectors


async def upsert_chapter_chunks(
    db: AsyncSession,
    *,
    project_id: int,
    chapter_number: int,
    content: str,
) -> int:
    settings = await load_app_settings(db)
    preset = get_embedding_preset(settings)
    chunks = split_chunks(content)
    await db.execute(
        delete(ChapterChunk).where(
            ChapterChunk.project_id == project_id,
            ChapterChunk.chapter_number == chapter_number,
        )
    )
    if not chunks:
        await db.commit()
        return 0
    vectors = await _embed_texts(preset, chunks)
    for idx, (chunk, vec) in enumerate(zip(chunks, vectors)):
        db.add(
            ChapterChunk(
                project_id=project_id,
                chapter_number=chapter_number,
                chunk_index=idx,
                content=chunk,
                embedding=vec,
            )
        )
    await db.commit()
    return len(chunks)


async def similarity_search(
    db: AsyncSession,
    *,
    project_id: int,
    query: str,
    top_k: int | None = None,
) -> list[dict[str, Any]]:
    settings = await load_app_settings(db)
    preset = get_embedding_preset(settings)
    k = top_k or int(preset.get("retrieval_k") or 4)
    vectors = await _embed_texts(preset, [query])
    query_vec = vectors[0]
    emb_literal = "[" + ",".join(f"{float(x):.8f}" for x in query_vec) + "]"
    sql = text(
        """
        SELECT id, chapter_number, chunk_index, content,
               embedding <=> CAST(:emb AS vector) AS distance
        FROM chapter_chunks
        WHERE project_id = :project_id
        ORDER BY embedding <=> CAST(:emb AS vector)
        LIMIT :top_k
        """
    )
    result = await db.execute(
        sql,
        {"project_id": project_id, "emb": emb_literal, "top_k": k},
    )
    rows = result.mappings().all()
    return [
        {
            "id": r["id"],
            "chapter_number": r["chapter_number"],
            "chunk_index": r["chunk_index"],
            "content": r["content"],
            "distance": float(r["distance"]) if r["distance"] is not None else None,
        }
        for r in rows
    ]


async def format_rag_context(db: AsyncSession, project_id: int, query: str) -> str:
    hits = await similarity_search(db, project_id=project_id, query=query)
    if not hits:
        return ""
    parts = []
    for h in hits:
        parts.append(f"[第{h['chapter_number']}章#{h['chunk_index']}] {h['content']}")
    return "\n\n".join(parts)

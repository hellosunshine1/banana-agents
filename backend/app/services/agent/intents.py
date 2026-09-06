from __future__ import annotations

import json
import re
from typing import Any

INTENTS = (
    "generate_architecture",
    "generate_blueprint",
    "generate_draft",
    "finalize_chapter",
    "consistency_check",
    "edit_artifact",
    "rag_query",
    "clarify",
    "reject",
)

INTENT_TO_TOOL = {
    "generate_architecture": "tool_generate_architecture",
    "generate_blueprint": "tool_generate_blueprint",
    "generate_draft": "tool_generate_draft",
    "finalize_chapter": "tool_finalize_chapter",
    "consistency_check": "tool_consistency_check",
    "rag_query": "tool_rag_query",
    # edit_artifact -> clarify (no write tool in M3)
    # clarify / reject -> no tool
}

_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("generate_architecture", re.compile(r"(生成|写).*(设定|架构|世界观)|设定生成|architecture", re.I)),
    ("generate_blueprint", re.compile(r"(生成|写).*(目录|大纲|蓝图)|目录生成|blueprint", re.I)),
    ("generate_draft", re.compile(r"(生成|写).*(草稿|正文|章节)|草稿生成|draft", re.I)),
    ("finalize_chapter", re.compile(r"定稿|finalize", re.I)),
    ("consistency_check", re.compile(r"审校|一致性|冲突检测|consistency", re.I)),
    ("edit_artifact", re.compile(r"(修改|编辑|改).*(设定|摘要|角色|目录|章节)|edit", re.I)),
    ("rag_query", re.compile(r"(检索|搜索|查找|rag).*(片段|章节|内容)?|向量检索", re.I)),
]


def rule_based_intent(message: str) -> str | None:
    text = (message or "").strip()
    if not text:
        return "clarify"
    for intent, pattern in _RULES:
        if pattern.search(text):
            return intent
    return None


def extract_chapter_number(message: str, default: int | None = None) -> int | None:
    m = re.search(r"第\s*(\d+)\s*章", message)
    if m:
        return int(m.group(1))
    m = re.search(r"chapter\s*(\d+)", message, re.I)
    if m:
        return int(m.group(1))
    return default


def extract_rag_query(message: str) -> str:
    cleaned = re.sub(r"(请|帮我)?(检索|搜索|查找|rag)(一下|相关)?", "", message, flags=re.I)
    return cleaned.strip() or message.strip()


async def classify_intent_with_llm(message: str, preset: dict[str, Any] | None) -> str:
    """Optional LLM classification; falls back to clarify on failure."""
    ruled = rule_based_intent(message)
    if ruled:
        return ruled
    if not preset or not (preset.get("api_key") or "").strip():
        return "clarify"
    try:
        from app.services.dify.fallback import chat_complete

        prompt = (
            "将用户消息分类为以下意图之一，只输出 JSON："
            '{"intent":"<name>"}。可选意图：'
            + ",".join(INTENTS)
            + f"\n用户消息：{message}"
        )
        text = await chat_complete(preset, prompt, system="你是意图分类器，只输出 JSON。")
        data = json.loads(text.strip().strip("`"))
        if isinstance(data, dict):
            intent = str(data.get("intent") or "").strip()
            if intent in INTENTS:
                return intent
    except Exception:
        pass
    return "clarify"

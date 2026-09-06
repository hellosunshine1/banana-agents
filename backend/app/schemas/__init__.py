from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    topic: str = ""
    genre: str = ""
    num_chapters: int = 0
    word_number: int = 0
    model_routing: dict[str, Any] | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    topic: str | None = None
    genre: str | None = None
    num_chapters: int | None = None
    word_number: int | None = None
    model_routing: dict[str, Any] | None = None
    architecture: str | None = None
    character_state: str | None = None
    global_summary: str | None = None
    status: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    name: str
    topic: str
    genre: str
    num_chapters: int
    word_number: int
    model_routing: dict[str, Any] | None
    architecture: str
    character_state: str
    global_summary: str
    status: str
    created_at: datetime
    updated_at: datetime


class SettingsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    llm_configs: dict[str, Any]
    embedding_configs: dict[str, Any]
    choose_configs: dict[str, Any]
    updated_at: datetime


class SettingsUpdate(BaseModel):
    llm_configs: dict[str, Any]
    embedding_configs: dict[str, Any]
    choose_configs: dict[str, Any]


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    type: str
    status: str
    progress: int
    result_ref: str | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class JobCreated(BaseModel):
    job_id: int


class BlueprintItem(BaseModel):
    chapter_number: int
    title: str = ""
    summary: str = ""
    raw_text: str = ""


class BlueprintListOut(BaseModel):
    items: list[BlueprintItem]


class BlueprintPut(BaseModel):
    items: list[BlueprintItem]


class ChapterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    chapter_number: int
    content: str
    status: str
    created_at: datetime
    updated_at: datetime


class ChapterUpdate(BaseModel):
    content: str


class DraftRequest(BaseModel):
    guidance: str = ""


class RagQueryRequest(BaseModel):
    query: str
    top_k: int | None = None


class RagHit(BaseModel):
    id: int
    chapter_number: int
    chunk_index: int
    content: str
    distance: float | None = None


class RagQueryOut(BaseModel):
    hits: list[RagHit]


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1)
    chapter_number: int | None = None
    guidance: str | None = None


class AgentChatResponse(BaseModel):
    intent: str
    tool: str | None = None
    job_id: int | None = None
    sse_endpoint: str | None = None
    message: str = ""
    data: dict[str, Any] | None = None


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    user_message: str
    intent: str
    tool_name: str | None
    tool_args: dict[str, Any] | None
    status: str
    result_summary: str
    created_at: datetime


class ConsistencyReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    chapter_number: int
    job_id: int | None
    conflicts: dict[str, Any]
    raw_text: str
    created_at: datetime

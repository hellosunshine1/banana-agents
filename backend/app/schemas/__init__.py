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

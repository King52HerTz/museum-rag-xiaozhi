from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Audience = Literal["child", "adult"]
TaskId = Literal["clothes-light-v1", "clothes-pattern-v1"]


class MobileProgressRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience: Audience
    completed_tasks: list[TaskId] = Field(default_factory=list, max_length=2)


class MobileProgressResponse(BaseModel):
    audience: Audience
    completed_tasks: list[TaskId]
    rewards: list[str]


class MobileRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class MobileSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience: Audience
    exhibit_id: Literal["silk-plain-straight", "silk-painted-robe"] | None = None


class MobileChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    audience: Audience
    session_id: str = Field(min_length=1, max_length=120)
    message: str = Field(min_length=1, max_length=8000)

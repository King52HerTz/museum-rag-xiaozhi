from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Audience = Literal["child", "adult"]


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

from __future__ import annotations

from pydantic import BaseModel, Field


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    character: str = Field(min_length=1, max_length=100)


class JobResult(BaseModel):
    status: str
    output_path: str
    prompt_id: str


class APIError(BaseModel):
    detail: str

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator


class Credentials(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr


class SourcePostCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)
    markdown: str | None = Field(default=None, min_length=20, max_length=100_000)
    url: HttpUrl | None = None

    @model_validator(mode="after")
    def exactly_one_source(self):
        if (self.markdown is None) == (self.url is None):
            raise ValueError("Provide exactly one of markdown or url")
        if self.markdown is not None and not self.title:
            raise ValueError("title is required for Markdown posts")
        return self


class VariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    platform: str
    content: str
    status: str
    rejection_reason: str | None
    reviewed_at: datetime | None
    updated_at: datetime
    created_at: datetime


class SourcePostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    content: str
    source_url: str | None
    content_hash: str
    created_at: datetime


class GenerateVariants(BaseModel):
    platforms: list[Literal["x", "linkedin"]] = Field(min_length=1)


class VariantEdit(BaseModel):
    content: str = Field(min_length=1, max_length=3_000)


class VariantReject(BaseModel):
    reason: str = Field(min_length=3, max_length=1_000)


class ScheduleCreate(BaseModel):
    publish_at: datetime

    @model_validator(mode="after")
    def timezone_is_required(self):
        if self.publish_at.tzinfo is None or self.publish_at.utcoffset() is None:
            raise ValueError("publish_at must include a timezone")
        return self


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    variant_id: int
    publish_at: datetime
    status: str
    created_at: datetime

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

import uuid
from datetime import datetime, timezone
from typing import Generic, TypeVar
from pydantic import BaseModel, model_validator

T = TypeVar("T")


class ORMBase(BaseModel):
    """Base for response models — handles UUID/datetime → str coercion."""
    model_config = {"from_attributes": True}

    @staticmethod
    def _fmt(val):
        if isinstance(val, datetime):
            if val.tzinfo is None:
                val = val.replace(tzinfo=timezone.utc)
            return val.isoformat()
        if isinstance(val, uuid.UUID):
            return str(val)
        return val

    @model_validator(mode="before")
    @classmethod
    def coerce_types(cls, data):
        if isinstance(data, dict):
            return {k: cls._fmt(v) for k, v in data.items()}
        # data is an ORM object — extract attributes and coerce
        collected = {}
        for field_name in cls.model_fields:
            val = getattr(data, field_name, None)
            collected[field_name] = cls._fmt(val)
        return collected


class ResponseModel(BaseModel, Generic[T]):
    code: int = 200
    message: str = "success"
    data: T | None = None


class PageInfo(BaseModel):
    page: int
    page_size: int
    total: int


class PageResponse(BaseModel, Generic[T]):
    items: list[T]
    pagination: PageInfo


class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 10

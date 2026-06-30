"""统一响应结构与分页工具。"""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class PageMeta(BaseModel):
    page: int
    page_size: int
    total: int


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


def ok(data=None, message: str = "ok") -> ApiResponse:
    return ApiResponse(code=0, message=message, data=data)

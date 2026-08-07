from typing import Any

from pydantic import BaseModel, Field


class PaginationMeta(BaseModel):
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)


class ChartPoint(BaseModel):
    label: str
    value: float


class AnalyticsResponse(BaseModel):
    items: list[dict[str, Any]]
    pagination: PaginationMeta
    chart_data: list[ChartPoint]


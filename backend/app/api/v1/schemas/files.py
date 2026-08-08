from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReportCreateRequest(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    search: str = Field(default="", max_length=100)

    @model_validator(mode="after")
    def valid_range(self) -> "ReportCreateRequest":
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValueError("start_date must be on or before end_date")
        return self


class FileAssetResponse(BaseModel):
    id: UUID
    kind: str
    original_name: str
    content_type: str
    size_bytes: int
    created_at: datetime
    view_url: str
    download_url: str


class FileAssetList(BaseModel):
    items: list[FileAssetResponse]
    count: int

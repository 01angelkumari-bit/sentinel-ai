from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel

class DatasetImportResponse(BaseModel):
    id: UUID
    file_name: str
    mode: str
    status: str
    total_rows: int
    processed_rows: int
    imported_rows: int
    progress_percent: int
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

class DatasetStatusResponse(BaseModel):
    has_data: bool
    record_count: int
    active_import: DatasetImportResponse | None
    history: list[DatasetImportResponse]

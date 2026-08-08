from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.files.sales_import import normalize_sales_file
from app.core.config import get_settings
from app.domain.users.models import DatasetImport, FileAsset


@dataclass(frozen=True)
class DatasetSource:
    import_id: UUID
    name: str
    path: Path
    mode: str


class TenantDatasetContext:
    """Reads only completed imports owned by the authenticated organization."""

    def __init__(self, db: Session, organization_id: UUID) -> None:
        self.db, self.organization_id = db, organization_id
        backend_root = Path(__file__).resolve().parents[3]
        configured = Path(get_settings().storage_root)
        self.storage_root = (configured if configured.is_absolute() else backend_root / configured).resolve()

    def active_sources(self) -> list[DatasetSource]:
        rows = self.db.execute(select(DatasetImport, FileAsset).join(FileAsset, FileAsset.id == DatasetImport.file_asset_id).where(DatasetImport.organization_id == self.organization_id, FileAsset.organization_id == self.organization_id, DatasetImport.status == "completed").order_by(DatasetImport.created_at)).all()
        if not rows:
            return []
        start = 0
        for index, (job, _) in enumerate(rows):
            if job.mode in {"initial", "replace"}:
                start = index
        sources: list[DatasetSource] = []
        for job, asset in rows[start:]:
            path = (self.storage_root / asset.relative_path).resolve()
            if self.storage_root not in path.parents or not path.is_file():
                continue
            sources.append(DatasetSource(job.id, asset.original_name, path, job.mode))
        return sources

    def select_source(self, question: str, prior_user_messages: list[str]) -> tuple[DatasetSource | None, list[DatasetSource]]:
        sources = self.active_sources()
        if not sources:
            return None, []
        context = " ".join([*prior_user_messages[-6:], question]).lower()
        named = [source for source in sources if source.name.lower() in context or Path(source.name).stem.lower() in context]
        if named:
            return named[-1], sources
        return (sources[0], sources) if len(sources) == 1 else (None, sources)

    def load(self, source: DatasetSource) -> pd.DataFrame:
        canonical, _, _ = normalize_sales_file(source.name, source.path.read_bytes())
        frame = pd.read_csv(io.BytesIO(canonical))
        frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce")
        for column in ("Revenue", "Orders", "Cancelled"):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        return frame

    def load_active(self) -> pd.DataFrame:
        frames = [self.load(source) for source in self.active_sources()]
        return pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()

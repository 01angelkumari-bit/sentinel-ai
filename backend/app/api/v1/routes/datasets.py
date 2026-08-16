from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_role
from app.api.v1.schemas.datasets import DatasetImportResponse, DatasetStatusResponse
from app.application.files.sales_import import SalesCsvImporter, delete_tenant_business_data, normalize_sales_file
from app.application.files.service import FileService
from app.core.config import get_settings
from app.domain.business.models import SalesOrder
from app.domain.users.models import DatasetImport, FileAsset, User
from app.infrastructure.database import get_db

router = APIRouter(prefix="/datasets", tags=["dataset onboarding"])
IMPORT_PROGRESS: dict[UUID, tuple[int, int]] = {}
PROGRESS_LOCK = Lock()

def _response(job: DatasetImport, file_name: str) -> DatasetImportResponse:
    with PROGRESS_LOCK:
        processed, total = IMPORT_PROGRESS.get(job.id, (int(job.processed_rows), int(job.total_rows)))
    percent = 100 if job.status == "completed" else min(99, int(processed * 100 / total)) if total else 0
    return DatasetImportResponse(id=job.id, file_name=file_name, mode=job.mode, status=job.status, total_rows=total, processed_rows=processed, imported_rows=int(job.imported_rows), progress_percent=percent, error_message=job.error_message, created_at=job.created_at, completed_at=job.completed_at)

def _tenant_context(db: Session, organization_id: UUID) -> None:
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.current_organization', :organization_id, true)"), {"organization_id": str(organization_id)})

def _process_import(job_id: UUID, organization_id: UUID, relative_path: str, original_name: str, mode: str, bind) -> None:
    with Session(bind=bind) as db:
        _tenant_context(db, organization_id)
        job = db.scalar(select(DatasetImport).where(DatasetImport.id == job_id, DatasetImport.organization_id == organization_id))
        if not job:
            return
        job.status = "processing"; db.commit()
        backend_root = Path(__file__).resolve().parents[4]
        configured = Path(get_settings().storage_root)
        storage_root = configured if configured.is_absolute() else backend_root / configured
        path = (storage_root / relative_path).resolve()
        try:
            data, total_rows, _ = normalize_sales_file(original_name, path.read_bytes())
            job.total_rows = total_rows
            db.commit()
            def progress(processed: int, total: int) -> None:
                with PROGRESS_LOCK:
                    IMPORT_PROGRESS[job_id] = (processed, total)
            imported = SalesCsvImporter(db, organization_id).import_if_supported("text/csv", data, replace=mode == "replace", progress=progress)
            _tenant_context(db, organization_id)
            job = db.scalar(select(DatasetImport).where(DatasetImport.id == job_id, DatasetImport.organization_id == organization_id))
            job.status = "completed"; job.processed_rows = job.total_rows; job.imported_rows = imported; job.completed_at = datetime.now(timezone.utc); db.commit()
        except Exception as exc:
            db.rollback(); _tenant_context(db, organization_id)
            job = db.scalar(select(DatasetImport).where(DatasetImport.id == job_id, DatasetImport.organization_id == organization_id))
            if job:
                job.status = "failed"; job.error_message = str(getattr(exc, "detail", exc))[:500]; job.completed_at = datetime.now(timezone.utc); db.commit()
        finally:
            with PROGRESS_LOCK:
                IMPORT_PROGRESS.pop(job_id, None)

@router.get("/status", response_model=DatasetStatusResponse)
def dataset_status(user: User = Depends(current_user), db: Session = Depends(get_db)) -> DatasetStatusResponse:
    count = int(db.scalar(select(func.count()).select_from(SalesOrder).where(SalesOrder.organization_id == user.organization_id)) or 0)
    rows = db.execute(select(DatasetImport, FileAsset.original_name).join(FileAsset, FileAsset.id == DatasetImport.file_asset_id).where(DatasetImport.organization_id == user.organization_id).order_by(DatasetImport.created_at.desc()).limit(25)).all()
    history = [_response(job, name) for job, name in rows]
    active = next((item for item in history if item.status in {"queued", "processing"}), None)
    return DatasetStatusResponse(has_data=count > 0, record_count=count, active_import=active, history=history)


@router.get("/presence")
def dataset_presence(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict[str, bool]:
    """Cheap route guard; full history and counts load only on onboarding."""
    has_data = db.scalar(select(SalesOrder.id).where(SalesOrder.organization_id == user.organization_id).limit(1)) is not None
    return {"has_data": has_data}

@router.post("/imports", response_model=DatasetImportResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_dataset_import(background: BackgroundTasks, request: Request, x_filename: str = Header(..., min_length=1, max_length=255), x_import_mode: Literal["initial", "append", "replace"] = Header("initial"), user: User = Depends(require_role("employee")), db: Session = Depends(get_db)) -> DatasetImportResponse:
    suffix = Path(x_filename).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise HTTPException(status_code=415, detail="Dataset onboarding accepts CSV or XLSX files")
    data = await request.body()
    if len(data) > get_settings().max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds the configured upload limit")
    existing = db.scalar(select(SalesOrder.id).where(SalesOrder.organization_id == user.organization_id).limit(1)) is not None
    if existing and x_import_mode == "initial":
        raise HTTPException(status_code=409, detail="A dataset already exists. Choose append or replace.")
    active = db.scalar(select(DatasetImport.id).where(DatasetImport.organization_id == user.organization_id, DatasetImport.status.in_(["queued", "processing"])))
    if active:
        raise HTTPException(status_code=409, detail="Another dataset import is already running")
    content_type = "text/csv" if suffix == ".csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    asset = FileService(db).save_upload(user.id, user.organization_id, x_filename, content_type, data)
    job = DatasetImport(organization_id=user.organization_id, uploaded_by_id=user.id, file_asset_id=asset.id, mode=x_import_mode, status="queued", total_rows=0)
    db.add(job); db.commit(); db.refresh(job)
    with PROGRESS_LOCK:
        IMPORT_PROGRESS[job.id] = (0, 0)
    background.add_task(_process_import, job.id, user.organization_id, asset.relative_path, asset.original_name, x_import_mode, db.get_bind())
    return _response(job, asset.original_name)

@router.delete("/current", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_dataset(user: User = Depends(require_role("manager")), db: Session = Depends(get_db)) -> Response:
    active = db.scalar(select(DatasetImport.id).where(DatasetImport.organization_id == user.organization_id, DatasetImport.status.in_(["queued", "processing"])))
    if active:
        raise HTTPException(status_code=409, detail="Wait for the active import to finish before deleting data")
    delete_tenant_business_data(db, user.organization_id); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

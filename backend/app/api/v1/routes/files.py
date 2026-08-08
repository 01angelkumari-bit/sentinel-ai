from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Request, Response, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.dependencies import current_user, require_role
from app.api.v1.schemas.files import FileAssetList, FileAssetResponse, ReportCreateRequest
from app.application.analytics.service import BusinessAnalyticsService
from app.application.audit import record_audit
from app.application.files.service import FileService
from app.domain.users.models import FileAsset, User
from app.infrastructure.database import get_db
from app.repositories.business_analytics import BusinessAnalyticsRepository

router = APIRouter(prefix="/files", tags=["files and reports"])


def response_for(asset: FileAsset) -> FileAssetResponse:
    return FileAssetResponse(
        id=asset.id, kind=asset.kind, original_name=asset.original_name, content_type=asset.content_type,
        size_bytes=asset.size_bytes, created_at=asset.created_at,
        view_url=f"/api/v1/files/{asset.id}/view", download_url=f"/api/v1/files/{asset.id}/download",
    )


@router.post("/reports", response_model=FileAssetResponse, status_code=status.HTTP_201_CREATED, summary="Generate and persist an executive PDF")
def create_report(payload: ReportCreateRequest, user: User = Depends(require_role("manager")), db: Session = Depends(get_db)) -> FileAssetResponse:
    analytics = BusinessAnalyticsService(BusinessAnalyticsRepository(db, user.organization_id))
    overview = analytics.overview(payload.start_date, payload.end_date)
    products = analytics.products(payload.start_date, payload.end_date, 10)
    regions = analytics.regions(payload.start_date, payload.end_date)
    report = {
        "overview": overview,
        "products": products,
        "regions": regions,
        "customers": analytics.customer_ltv(10),
        "search": payload.search.strip(),
        "generated_at": datetime.now(timezone.utc).strftime("%d %B %Y, %H:%M UTC"),
    }
    asset = FileService(db).save_report(user.id, user.organization_id, report)
    record_audit(db, user.organization_id, user.id, "report.generated", "file_asset", asset.id); db.commit()
    return response_for(asset)


@router.post("/uploads", response_model=FileAssetResponse, status_code=status.HTTP_201_CREATED, summary="Upload a CSV, XLSX, or PDF file")
async def upload_file(
    request: Request,
    x_filename: str = Header(..., min_length=1, max_length=255),
    content_type: str = Header(...),
    user: User = Depends(require_role("employee")),
    db: Session = Depends(get_db),
) -> FileAssetResponse:
    data = await request.body()
    normalized_type = content_type.split(";", 1)[0].lower()
    asset = FileService(db).save_upload(user.id, user.organization_id, x_filename, normalized_type, data)
    record_audit(db, user.organization_id, user.id, "file.uploaded", "file_asset", asset.id, {"filename": asset.original_name, "size": asset.size_bytes}); db.commit()
    return response_for(asset)


@router.get("", response_model=FileAssetList, summary="List generated reports and uploaded files")
def list_files(user: User = Depends(current_user), db: Session = Depends(get_db)) -> FileAssetList:
    items = [response_for(asset) for asset in FileService(db).list(user.organization_id)]
    return FileAssetList(items=items, count=len(items))


@router.get("/{asset_id}/view", summary="Open a stored file inline")
def view_file(asset_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> FileResponse:
    asset, path = FileService(db).get(asset_id, user.organization_id)
    record_audit(db, user.organization_id, user.id, "file.viewed", "file_asset", asset.id); db.commit()
    return FileResponse(path, media_type=asset.content_type, filename=asset.original_name, content_disposition_type="inline")


@router.get("/{asset_id}/download", summary="Download a stored file")
def download_file(asset_id: UUID, user: User = Depends(current_user), db: Session = Depends(get_db)) -> FileResponse:
    asset, path = FileService(db).get(asset_id, user.organization_id)
    record_audit(db, user.organization_id, user.id, "file.downloaded", "file_asset", asset.id); db.commit()
    return FileResponse(path, media_type=asset.content_type, filename=asset.original_name, content_disposition_type="attachment")


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a stored file")
def delete_file(asset_id: UUID, user: User = Depends(require_role("manager")), db: Session = Depends(get_db)) -> Response:
    FileService(db).delete(asset_id, user.organization_id)
    record_audit(db, user.organization_id, user.id, "file.deleted", "file_asset", asset_id); db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

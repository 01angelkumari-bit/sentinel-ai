from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

from app.core.config import get_settings
from app.domain.users.models import FileAsset

ALLOWED_UPLOADS = {
    "text/csv": ".csv",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


NAVY = HexColor("#0B1220")
SLATE = HexColor("#334155")
MUTED = HexColor("#64748B")
LIGHT = HexColor("#E2E8F0")
PANEL = HexColor("#F8FAFC")
VIOLET = HexColor("#7C3AED")
BLUE = HexColor("#2563EB")
GREEN = HexColor("#16A34A")
AMBER = HexColor("#D97706")
RED = HexColor("#DC2626")


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _compact_money(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:,.2f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:,.1f}K"
    return _money(value)


def _percent(value: float | None) -> str:
    return "N/A" if value is None else f"{value:+.2f}%"


def _chart(values: list[float], labels: list[str], title: str, *, horizontal: bool = False) -> Drawing:
    drawing = Drawing(245 * mm, 52 * mm)
    drawing.add(String(0, 140, title, fontName="Helvetica-Bold", fontSize=11, fillColor=NAVY))
    chart = HorizontalBarChart() if horizontal else VerticalBarChart()
    chart.x = 40 if horizontal else 38
    chart.y = 20
    chart.width = 620
    chart.height = 100
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.valueAxis.valueMin = 0
    chart.valueAxis.valueMax = max(values or [1]) * 1.15
    chart.valueAxis.valueStep = max(1, chart.valueAxis.valueMax / 5)
    chart.valueAxis.labelTextFormat = lambda value: f"${value / 1_000_000:.1f}M" if value >= 1_000_000 else f"${value / 1_000:.0f}K"
    chart.bars[0].fillColor = VIOLET
    chart.bars[0].strokeColor = VIOLET
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    if not horizontal:
        chart.categoryAxis.labels.angle = 20
        chart.categoryAxis.labels.dy = -8
    drawing.add(chart)
    return drawing


def build_pdf(report: dict) -> bytes:
    buffer = BytesIO()
    page_width, page_height = landscape(A4)
    document = BaseDocTemplate(buffer, pagesize=(page_width, page_height), leftMargin=18 * mm, rightMargin=18 * mm, topMargin=20 * mm, bottomMargin=16 * mm, title="Sentinel AI Executive Business Analytics Report", author="Sentinel AI")
    document.addPageTemplates(PageTemplate(id="report", frames=[Frame(document.leftMargin, document.bottomMargin, document.width, document.height, id="body")], onPageEnd=_draw_page))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27, leading=31, textColor=NAVY, alignment=TA_LEFT, spaceAfter=5 * mm))
    styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=11, leading=17, textColor=MUTED, spaceAfter=4 * mm))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=NAVY, spaceBefore=3 * mm, spaceAfter=4 * mm))
    styles.add(ParagraphStyle(name="SmallHeading", parent=styles["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=NAVY, spaceAfter=2 * mm))
    styles.add(ParagraphStyle(name="BodyCopy", parent=styles["BodyText"], fontSize=9, leading=14, textColor=SLATE))
    styles.add(ParagraphStyle(name="Fine", parent=styles["BodyText"], fontSize=7.5, leading=11, textColor=MUTED))
    overview = report["overview"]
    products = report["products"]
    regions = report["regions"]
    customers = report["customers"]
    generated = report["generated_at"]
    period = f"{overview['start_date']} to {overview['end_date']}" if overview["start_date"] or overview["end_date"] else "All available business records"
    story = []

    story.extend([
        Spacer(1, 5 * mm),
        Paragraph("SENTINEL AI / EXECUTIVE INTELLIGENCE", styles["SmallHeading"]),
        Paragraph("Executive Business Analytics Report", styles["ReportTitle"]),
        Paragraph("A decision-ready view of commercial performance, profitability, growth, regional contribution, product demand, and customer value.", styles["Subtitle"]),
        _info_table([["REPORTING PERIOD", period], ["GENERATED", generated], ["SEARCH CONTEXT", report.get("search") or "No search filter"], ["DATA POLICY", "Recognized revenue from non-cancelled orders"]], styles),
        Spacer(1, 3 * mm),
        Paragraph("Executive snapshot", styles["Section"]),
        _kpi_table(overview, styles),
        Spacer(1, 3 * mm),
        Paragraph(_executive_commentary(overview, products, regions), styles["BodyCopy"]),
        Spacer(1, 2 * mm),
        _growth_table(overview, styles),
        PageBreak(),
        Paragraph("Product performance", styles["Section"]),
        Paragraph("Top-selling products ranked by recognized revenue, with unit volume, order reach, profitability, and gross-margin contribution.", styles["Subtitle"]),
        _chart([item["revenue"] for item in products[:8]], [item["product"][:18] for item in products[:8]], "Revenue by top product"),
        Spacer(1, 1 * mm),
        _product_table(products, styles),
        PageBreak(),
        Paragraph("Regional performance", styles["Section"]),
        Paragraph("A comparative view of customer coverage, order activity, revenue, profit, average order value, and share of total revenue.", styles["Subtitle"]),
        _chart([item["revenue"] for item in regions], [item["region"] for item in regions], "Revenue contribution by region", horizontal=True),
        Spacer(1, 1 * mm),
        _region_table(regions, styles),
        PageBreak(),
        Paragraph("Customer lifetime value", styles["Section"]),
        Paragraph("Realized lifetime value represents cumulative recognized revenue from each customer's non-cancelled orders.", styles["Subtitle"]),
        _customer_table(customers, styles),
        Spacer(1, 3 * mm),
        Paragraph("Management interpretation", styles["Section"]),
        _recommendations(report, styles),
        PageBreak(),
        Paragraph("Metric definitions and audit notes", styles["Section"]),
        _definitions(styles),
        Spacer(1, 7 * mm),
        Paragraph("Report integrity", styles["SmallHeading"]),
        Paragraph("This report was generated from Sentinel AI's normalized business-intelligence database. Source records remain auditable through the protected API. Filters are inclusive. Cancelled sales orders are excluded from revenue, profit, average-order-value, product, regional, and customer-lifetime-value calculations.", styles["BodyCopy"]),
        Spacer(1, 6 * mm),
        Paragraph("Confidentiality", styles["SmallHeading"]),
        Paragraph("Confidential business information. Distribution should follow your organization's data-governance and access-control policies.", styles["BodyCopy"]),
    ])
    document.build(story)
    return buffer.getvalue()


def _draw_page(canvas, document) -> None:
    canvas.saveState()
    width, height = landscape(A4)
    canvas.setFillColor(NAVY)
    canvas.rect(0, height - 12 * mm, width, 12 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(18 * mm, height - 7.5 * mm, "SENTINEL AI")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 18 * mm, height - 7.5 * mm, "Executive Business Analytics")
    canvas.setStrokeColor(LIGHT)
    canvas.line(18 * mm, 11 * mm, width - 18 * mm, 11 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(18 * mm, 6.5 * mm, "Confidential - Generated from normalized Sentinel AI business data")
    canvas.drawRightString(width - 18 * mm, 6.5 * mm, f"Page {document.page}")
    canvas.restoreState()


def _styled_table(data, widths, *, header=True, alignments=None, row_heights=None) -> Table:
    table = Table(data, colWidths=widths, rowHeights=row_heights, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [("FONTNAME", (0, 0), (-1, -1), "Helvetica"), ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("TEXTCOLOR", (0, 0), (-1, -1), SLATE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("GRID", (0, 0), (-1, -1), .35, LIGHT)]
    if header:
        commands.extend([("BACKGROUND", (0, 0), (-1, 0), NAVY), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")])
        if len(data) > 1: commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PANEL]))
    if alignments:
        for column, alignment in enumerate(alignments): commands.append(("ALIGN", (column, 0), (column, -1), alignment))
    table.setStyle(TableStyle(commands))
    return table


def _info_table(rows, styles) -> Table:
    data = [[Paragraph(label, styles["Fine"]), Paragraph(str(value), styles["BodyCopy"])] for label, value in rows]
    table = _styled_table(data, [42 * mm, 190 * mm], header=False)
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), PANEL), ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold")]))
    return table


def _kpi_table(overview, styles) -> Table:
    labels = ["Revenue", "Gross profit", "Gross margin", "Average order value", "Orders", "Customers"]
    values = [_compact_money(overview["revenue"]), _compact_money(overview["profit"]), f"{overview['gross_margin_percent']:.2f}%", _compact_money(overview["average_order_value"]), f"{overview['order_count']:,}", f"{overview['customer_count']:,}"]
    data = [[Paragraph(label.upper(), styles["Fine"]) for label in labels], [Paragraph(value, ParagraphStyle(name=f"kpi{index}", parent=styles["BodyCopy"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=[VIOLET, GREEN, BLUE, AMBER, NAVY, NAVY][index])) for index, value in enumerate(values)]]
    table = Table(data, colWidths=[39 * mm] * 6, rowHeights=[10 * mm, 16 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL), ("BOX", (0, 0), (-1, -1), .6, LIGHT), ("INNERGRID", (0, 0), (-1, -1), .4, LIGHT), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    return table


def _growth_table(overview, styles) -> Table:
    mom, wow = overview["mom_growth"], overview["wow_growth"]
    data = [["Growth metric", "Previous period", "Current period", "Previous revenue", "Current revenue", "Change"], ["Month over month", mom["previous_period"] or "N/A", mom["current_period"] or "N/A", _money(mom["previous_revenue"]), _money(mom["current_revenue"]), _percent(mom["growth_percent"])], ["Week over week", wow["previous_period"] or "N/A", wow["current_period"] or "N/A", _money(wow["previous_revenue"]), _money(wow["current_revenue"]), _percent(wow["growth_percent"])]]
    return _styled_table(data, [42 * mm, 39 * mm, 39 * mm, 41 * mm, 41 * mm, 28 * mm], alignments=["LEFT", "CENTER", "CENTER", "RIGHT", "RIGHT", "RIGHT"])


def _product_table(products, styles) -> Table:
    data = [["#", "Product", "SKU", "Units", "Orders", "Revenue", "Profit", "Gross margin"]]
    data += [[index, item["product"], item["sku"], f"{item['units_sold']:,}", f"{item['orders']:,}", _money(item["revenue"]), _money(item["profit"]), f"{item['gross_margin_percent']:.2f}%"] for index, item in enumerate(products, 1)]
    return _styled_table(data, [10 * mm, 50 * mm, 28 * mm, 22 * mm, 22 * mm, 34 * mm, 34 * mm, 30 * mm], alignments=["CENTER", "LEFT", "LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"])


def _region_table(regions, styles) -> Table:
    data = [["Region", "Customers", "Orders", "Revenue", "Profit", "Average order value", "Revenue share"]]
    data += [[item["region"], f"{item['customers']:,}", f"{item['orders']:,}", _money(item["revenue"]), _money(item["profit"]), _money(item["average_order_value"]), f"{item['revenue_share_percent']:.2f}%"] for item in regions]
    return _styled_table(data, [46 * mm, 28 * mm, 28 * mm, 38 * mm, 38 * mm, 45 * mm, 34 * mm], alignments=["LEFT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT", "RIGHT"])


def _customer_table(customers, styles) -> Table:
    data = [["#", "Customer", "Region", "First order", "Last order", "Orders", "Lifetime value", "Avg. order value"]]
    data += [[index, item["customer"], item["region"], str(item["first_order_date"]), str(item["last_order_date"]), f"{item['orders']:,}", _money(item["lifetime_value"]), _money(item["average_order_value"])] for index, item in enumerate(customers, 1)]
    return _styled_table(data, [10 * mm, 55 * mm, 31 * mm, 29 * mm, 29 * mm, 20 * mm, 37 * mm, 37 * mm], alignments=["CENTER", "LEFT", "LEFT", "CENTER", "CENTER", "RIGHT", "RIGHT", "RIGHT"])


def _executive_commentary(overview, products, regions) -> str:
    top_product = products[0]["product"] if products else "No product"
    top_region = regions[0]["region"] if regions else "No region"
    return f"The selected period produced <b>{_money(overview['revenue'])}</b> in recognized revenue and <b>{_money(overview['profit'])}</b> in gross profit, representing a <b>{overview['gross_margin_percent']:.2f}%</b> gross margin. <b>{top_product}</b> leads product revenue, while <b>{top_region}</b> is the highest-contributing region. Leadership should interpret the latest month and week with care when the reporting period ends before a calendar period is complete."


def _recommendations(report, styles) -> Table:
    overview, products, regions = report["overview"], report["products"], report["regions"]
    top_product = products[0] if products else None
    top_region = regions[0] if regions else None
    actions = [
        ["1", "Protect margin", f"Review discounting and delivery costs to sustain the current {overview['gross_margin_percent']:.2f}% gross margin."],
        ["2", "Scale product demand", f"Align inventory and account campaigns around {top_product['product'] if top_product else 'the leading product'} while monitoring concentration risk."],
        ["3", "Deepen regional coverage", f"Use {top_region['region'] if top_region else 'the leading region'} as the benchmark for pipeline quality, retention, and cross-sell execution."],
        ["4", "Review growth cadence", f"Investigate the drivers behind MoM {_percent(overview['mom_growth']['growth_percent'])} and WoW {_percent(overview['wow_growth']['growth_percent'])} before committing forecasts."],
    ]
    return _styled_table([["Priority", "Management action", "Rationale"], *actions], [20 * mm, 48 * mm, 165 * mm], alignments=["CENTER", "LEFT", "LEFT"])


def _definitions(styles) -> Table:
    definitions = [["Revenue", "Quantity multiplied by unit price, less line-item discounts, for non-cancelled sales orders."], ["Gross profit", "Revenue less product unit cost for recognized sales order items."], ["Gross margin", "Gross profit divided by revenue."], ["MoM / WoW growth", "Percentage change between the latest two calendar month or Sunday-ending week revenue buckets."], ["Average order value", "Recognized revenue divided by distinct non-cancelled orders."], ["Customer lifetime value", "Cumulative recognized revenue for a customer across all non-cancelled historical orders."], ["Revenue share", "Regional recognized revenue divided by total recognized revenue for the selected period."]]
    return _styled_table([["Metric", "Definition"], *definitions], [48 * mm, 185 * mm], alignments=["LEFT", "LEFT"])


class FileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        backend_root = Path(__file__).resolve().parents[3]
        configured = Path(get_settings().storage_root)
        self.storage_root = configured if configured.is_absolute() else backend_root / configured
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _save(self, owner_id: UUID, organization_id: UUID, kind: str, original_name: str, content_type: str, data: bytes) -> FileAsset:
        extension = Path(original_name).suffix.lower()
        stored_name = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{uuid4().hex}{extension}"
        relative = Path(str(organization_id)) / ("reports" if kind == "report" else "uploads") / stored_name
        destination = (self.storage_root / relative).resolve()
        if self.storage_root.resolve() not in destination.parents:
            raise HTTPException(status_code=400, detail="Invalid storage path")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            destination.write_bytes(data)
        except OSError as exc:
            raise HTTPException(status_code=500, detail="The file could not be saved") from exc
        if not destination.is_file() or destination.stat().st_size != len(data):
            destination.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail="File verification failed")
        asset = FileAsset(owner_id=owner_id, organization_id=organization_id, kind=kind, original_name=original_name, stored_name=stored_name, content_type=content_type, size_bytes=len(data), relative_path=relative.as_posix())
        self.db.add(asset)
        try:
            self.db.commit()
            self.db.refresh(asset)
        except Exception:
            self.db.rollback()
            destination.unlink(missing_ok=True)
            raise
        return asset

    def save_report(self, owner_id: UUID, organization_id: UUID, report: dict) -> FileAsset:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
        return self._save(owner_id, organization_id, "report", f"sentinel-executive-report-{timestamp}.pdf", "application/pdf", build_pdf(report))

    def save_upload(self, owner_id: UUID, organization_id: UUID, original_name: str, content_type: str, data: bytes) -> FileAsset:
        safe_name = Path(original_name).name.strip()
        expected_extension = ALLOWED_UPLOADS.get(content_type)
        if not safe_name or not expected_extension or Path(safe_name).suffix.lower() != expected_extension:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only CSV, XLSX, and PDF files are supported")
        if not data:
            raise HTTPException(status_code=422, detail="Uploaded file is empty")
        if len(data) > get_settings().max_upload_bytes:
            raise HTTPException(status_code=413, detail="File exceeds the 10 MB upload limit")
        extension = Path(safe_name).suffix.lower()
        if extension == ".pdf" and not data.startswith(b"%PDF-"):
            raise HTTPException(status_code=422, detail="The PDF signature is invalid")
        if extension == ".xlsx" and not data.startswith(b"PK"):
            raise HTTPException(status_code=422, detail="The Excel workbook signature is invalid")
        if extension == ".csv" and b"\x00" in data[:4096]:
            raise HTTPException(status_code=422, detail="The CSV contains invalid binary data")
        return self._save(owner_id, organization_id, "upload", safe_name, content_type, data)

    def get(self, asset_id: UUID, organization_id: UUID) -> tuple[FileAsset, Path]:
        asset = self.db.scalar(select(FileAsset).where(FileAsset.id == asset_id, FileAsset.organization_id == organization_id))
        if not asset:
            raise HTTPException(status_code=404, detail="File not found")
        path = (self.storage_root / asset.relative_path).resolve()
        if self.storage_root.resolve() not in path.parents or not path.is_file():
            raise HTTPException(status_code=410, detail="Stored file is no longer available")
        return asset, path

    def list(self, organization_id: UUID) -> list[FileAsset]:
        return list(self.db.scalars(select(FileAsset).where(FileAsset.organization_id == organization_id).order_by(FileAsset.created_at.desc()).limit(100)))

    def delete(self, asset_id: UUID, organization_id: UUID) -> None:
        asset, path = self.get(asset_id, organization_id)
        self.db.delete(asset)
        self.db.commit()
        path.unlink(missing_ok=True)

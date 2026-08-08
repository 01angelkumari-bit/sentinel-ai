import { NextRequest, NextResponse } from "next/server";
import type { BusinessAnalyticsSummary } from "@/components/dashboard/types";
import { authorizedBackendFetch } from "@/lib/server-api";

const cell = (value: string | number | null) => {
  let text = String(value ?? "");
  if (/^[=+\-@]/.test(text)) text = `'${text}`;
  return /[",\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

export async function GET(request: NextRequest) {
  const params = new URLSearchParams();
  const start = request.nextUrl.searchParams.get("start_date");
  const end = request.nextUrl.searchParams.get("end_date");
  const search = request.nextUrl.searchParams.get("q")?.trim().toLowerCase() ?? "";
  if (start) params.set("start_date", start);
  if (end) params.set("end_date", end);
  params.set("product_limit", "50");
  params.set("customer_limit", "50");
  const response = await authorizedBackendFetch(`/analytics/summary?${params}`);
  if (!response) return NextResponse.json({ detail: "Authentication required" }, { status: 401 });
  if (!response.ok) return NextResponse.json({ detail: "Analytics export is unavailable" }, { status: response.status });
  const data = await response.json() as BusinessAnalyticsSummary;
  const rows: Array<Array<string | number | null>> = [
    ["Section", "Name", "Region", "Orders/Units", "Revenue/LTV", "Profit", "Margin/Share %"],
    ["Overview", "Revenue", "", data.overview.order_count, data.overview.revenue, data.overview.profit, data.overview.gross_margin_percent],
    ...data.top_selling_products.filter(item => !search || `${item.product} ${item.sku}`.toLowerCase().includes(search)).map(item => ["Product", item.product, "", item.units_sold, item.revenue, item.profit, item.gross_margin_percent]),
    ...data.regional_performance.filter(item => !search || item.region.toLowerCase().includes(search)).map(item => ["Region", item.region, item.region, item.orders, item.revenue, item.profit, item.revenue_share_percent]),
    ...data.top_customers_by_ltv.filter(item => !search || `${item.customer} ${item.region}`.toLowerCase().includes(search)).map(item => ["Customer", item.customer, item.region, item.orders, item.lifetime_value, "", ""]),
  ];
  const csv = `\uFEFF${rows.map(row => row.map(cell).join(",")).join("\r\n")}\r\n`;
  return new NextResponse(csv, { headers: { "Content-Type": "text/csv; charset=utf-8", "Content-Disposition": `attachment; filename="sentinel-analytics-${new Date().toISOString().slice(0, 10)}.csv"`, "Cache-Control": "private, no-store" } });
}

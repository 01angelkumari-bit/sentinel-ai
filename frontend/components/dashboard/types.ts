export type MetricPoint = { label: string; value: number };
export type AlertItem = { severity: "high" | "medium" | "low"; title: string; description: string; confidence: number };
export type RecommendationItem = { title: string; description: string; impact: string; priority: "high" | "medium" | "low" };

export type DashboardSummary = {
  revenue: number;
  profit: number;
  cash_balance: number;
  open_tickets: number;
  employees: number;
  revenue_overview: MetricPoint[];
  revenue_by_region: MetricPoint[];
  top_products: MetricPoint[];
  customer_sentiment: MetricPoint[];
  sentiment_available: boolean;
  sentiment_score: number | null;
  sentiment_label: string | null;
  sentiment_message: string;
  recent_alerts: AlertItem[];
  recommendations: RecommendationItem[];
  source_counts: Record<"sales" | "finance" | "inventory" | "support" | "employees" | "customers", number>;
};

export type PeriodGrowth = {
  current_period: string | null;
  previous_period: string | null;
  current_revenue: number;
  previous_revenue: number;
  growth_percent: number | null;
};

export type ProductPerformance = { product_id: string; product: string; sku: string; units_sold: number; orders: number; revenue: number; profit: number; gross_margin_percent: number };
export type RegionPerformance = { region: string; customers: number; orders: number; revenue: number; profit: number; average_order_value: number; revenue_share_percent: number };
export type CustomerLtv = { customer_id: string; customer: string; region: string; first_order_date: string; last_order_date: string; orders: number; lifetime_value: number; average_order_value: number };
export type BusinessAnalyticsSummary = {
  overview: { start_date: string | null; end_date: string | null; revenue: number; profit: number; gross_margin_percent: number; average_order_value: number; order_count: number; customer_count: number; mom_growth: PeriodGrowth; wow_growth: PeriodGrowth };
  top_selling_products: ProductPerformance[];
  regional_performance: RegionPerformance[];
  top_customers_by_ltv: CustomerLtv[];
};

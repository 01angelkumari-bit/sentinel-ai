export type MetricPoint = { label: string; value: number };
export type AlertItem = { severity: "high" | "medium" | "low"; title: string; description: string };
export type RecommendationItem = { title: string; description: string; impact: string };

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
  recent_alerts: AlertItem[];
  recommendations: RecommendationItem[];
};


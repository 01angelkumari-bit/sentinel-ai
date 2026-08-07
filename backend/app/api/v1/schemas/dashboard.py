from pydantic import BaseModel


class MetricPoint(BaseModel):
    label: str
    value: float


class AlertItem(BaseModel):
    severity: str
    title: str
    description: str


class RecommendationItem(BaseModel):
    title: str
    description: str
    impact: str


class DashboardSummary(BaseModel):
    revenue: float
    profit: float
    cash_balance: float
    open_tickets: int
    employees: int
    revenue_overview: list[MetricPoint]
    revenue_by_region: list[MetricPoint]
    top_products: list[MetricPoint]
    customer_sentiment: list[MetricPoint]
    recent_alerts: list[AlertItem]
    recommendations: list[RecommendationItem]


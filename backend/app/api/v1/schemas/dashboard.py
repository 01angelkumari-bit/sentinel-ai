from pydantic import BaseModel


class MetricPoint(BaseModel):
    label: str
    value: float


class AlertItem(BaseModel):
    severity: str
    title: str
    description: str
    confidence: int


class RecommendationItem(BaseModel):
    title: str
    description: str
    impact: str
    priority: str


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
    sentiment_available: bool
    sentiment_score: float | None
    sentiment_label: str | None
    sentiment_message: str
    recent_alerts: list[AlertItem]
    recommendations: list[RecommendationItem]
    source_counts: dict[str, int]

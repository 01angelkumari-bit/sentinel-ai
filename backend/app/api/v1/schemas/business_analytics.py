from datetime import date

from pydantic import BaseModel, Field


class PeriodGrowth(BaseModel):
    current_period: str | None
    previous_period: str | None
    current_revenue: float = 0
    previous_revenue: float = 0
    growth_percent: float | None


class AnalyticsOverview(BaseModel):
    start_date: date | None
    end_date: date | None
    revenue: float
    profit: float
    gross_margin_percent: float
    average_order_value: float
    order_count: int
    customer_count: int
    mom_growth: PeriodGrowth
    wow_growth: PeriodGrowth


class ProductPerformance(BaseModel):
    product_id: str
    product: str
    sku: str
    units_sold: int
    orders: int
    revenue: float
    profit: float
    gross_margin_percent: float


class RegionalPerformance(BaseModel):
    region: str
    customers: int
    orders: int
    revenue: float
    profit: float
    average_order_value: float
    revenue_share_percent: float


class CustomerLifetimeValue(BaseModel):
    customer_id: str
    customer: str
    region: str
    first_order_date: date
    last_order_date: date
    orders: int
    lifetime_value: float
    average_order_value: float


class RankedResponse(BaseModel):
    items: list[ProductPerformance] | list[RegionalPerformance] | list[CustomerLifetimeValue]
    count: int = Field(ge=0)


class BusinessAnalyticsSummary(BaseModel):
    overview: AnalyticsOverview
    top_selling_products: list[ProductPerformance]
    regional_performance: list[RegionalPerformance]
    top_customers_by_ltv: list[CustomerLifetimeValue]


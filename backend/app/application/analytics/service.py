from datetime import date
from decimal import Decimal
from typing import Any

import pandas as pd

from app.repositories.business_analytics import BusinessAnalyticsRepository


class BusinessAnalyticsService:
    def __init__(self, repository: BusinessAnalyticsRepository) -> None:
        self.repository = repository

    @staticmethod
    def _number(value: Any) -> float:
        return round(float(value or 0), 2)

    @classmethod
    def _growth(cls, series: pd.Series) -> dict[str, Any]:
        if series.empty:
            return {"current_period": None, "previous_period": None, "current_revenue": 0, "previous_revenue": 0, "growth_percent": None}
        current_label = str(series.index[-1])
        current = cls._number(series.iloc[-1])
        if len(series) < 2:
            return {"current_period": current_label, "previous_period": None, "current_revenue": current, "previous_revenue": 0, "growth_percent": None}
        previous_label = str(series.index[-2])
        previous = cls._number(series.iloc[-2])
        growth = round(((current - previous) / previous) * 100, 2) if previous else None
        return {"current_period": current_label, "previous_period": previous_label, "current_revenue": current, "previous_revenue": previous, "growth_percent": growth}

    def growth(self, start_date: date | None, end_date: date | None) -> dict[str, Any]:
        frame = pd.DataFrame(self.repository.daily_revenue(start_date, end_date))
        if frame.empty:
            empty = self._growth(pd.Series(dtype="float64"))
            return {"mom_growth": empty, "wow_growth": empty.copy()}
        frame["date"] = pd.to_datetime(frame["date"])
        frame["revenue"] = pd.to_numeric(frame["revenue"])
        frame = frame.set_index("date").sort_index()
        monthly = frame["revenue"].resample("ME").sum()
        weekly = frame["revenue"].resample("W-SUN").sum()
        return {"mom_growth": self._growth(monthly), "wow_growth": self._growth(weekly)}

    def overview(self, start_date: date | None, end_date: date | None) -> dict[str, Any]:
        totals = self.repository.totals(start_date, end_date)
        revenue = self._number(totals["revenue"])
        profit = self._number(totals["profit"])
        order_count = int(totals["order_count"] or 0)
        growth = self.growth(start_date, end_date)
        return {
            "start_date": start_date, "end_date": end_date, "revenue": revenue, "profit": profit,
            "gross_margin_percent": round((profit / revenue) * 100, 2) if revenue else 0,
            "average_order_value": round(revenue / order_count, 2) if order_count else 0,
            "order_count": order_count, "customer_count": int(totals["customer_count"] or 0), **growth,
        }

    def products(self, start_date: date | None, end_date: date | None, limit: int) -> list[dict[str, Any]]:
        items = self.repository.products(start_date, end_date, limit)
        for item in items:
            item["product_id"] = str(item["product_id"])
            item["units_sold"] = int(item["units_sold"] or 0)
            item["orders"] = int(item["orders"] or 0)
            item["revenue"] = self._number(item["revenue"])
            item["profit"] = self._number(item["profit"])
            item["gross_margin_percent"] = round(item["profit"] / item["revenue"] * 100, 2) if item["revenue"] else 0
        return items

    def regions(self, start_date: date | None, end_date: date | None) -> list[dict[str, Any]]:
        items = self.repository.regions(start_date, end_date)
        total_revenue = sum(Decimal(str(item["revenue"] or 0)) for item in items)
        for item in items:
            item["customers"] = int(item["customers"] or 0)
            item["orders"] = int(item["orders"] or 0)
            item["revenue"] = self._number(item["revenue"])
            item["profit"] = self._number(item["profit"])
            item["average_order_value"] = round(item["revenue"] / item["orders"], 2) if item["orders"] else 0
            item["revenue_share_percent"] = round(float(Decimal(str(item["revenue"])) / total_revenue * 100), 2) if total_revenue else 0
        return items

    def customer_ltv(self, limit: int) -> list[dict[str, Any]]:
        items = self.repository.customer_ltv(limit)
        for item in items:
            item["customer_id"] = str(item["customer_id"])
            item["orders"] = int(item["orders"] or 0)
            item["lifetime_value"] = self._number(item["lifetime_value"])
            item["average_order_value"] = round(item["lifetime_value"] / item["orders"], 2) if item["orders"] else 0
        return items


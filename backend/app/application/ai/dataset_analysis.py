from __future__ import annotations

from dataclasses import asdict, dataclass
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


TEXT_SENTIMENT_NAMES = {"feedback", "review", "reviews", "comment", "comments", "customer_feedback", "customer_review", "review_text"}
RATING_NAMES = {"rating", "ratings", "stars", "star_rating", "review_score", "satisfaction_score", "sentiment_score"}


@dataclass(frozen=True)
class Risk:
    category: str
    severity: str
    metric: str
    actual_value: float
    threshold: str
    explanation: str
    evidence: str
    recommendation: str


def _normalized(column: object) -> str:
    return "_".join(str(column).strip().lower().replace("-", " ").split())


def profile_dataset(frame: pd.DataFrame) -> dict:
    missing = {str(column): int(frame[column].isna().sum()) for column in frame.columns if frame[column].isna().any()}
    numeric = [str(column) for column in frame.select_dtypes(include="number").columns]
    dates = [str(column) for column in frame.columns if pd.api.types.is_datetime64_any_dtype(frame[column])]
    categorical = [str(column) for column in frame.columns if str(column) not in numeric and str(column) not in dates and frame[column].nunique(dropna=True) <= max(20, len(frame) // 20)]
    text = [str(column) for column in frame.columns if str(column) not in numeric and str(column) not in dates and str(column) not in categorical]
    return {"row_count": len(frame), "column_count": len(frame.columns), "columns": [str(c) for c in frame.columns], "column_types": {str(c): str(frame[c].dtype) for c in frame.columns}, "numeric_columns": numeric, "date_columns": dates, "categorical_columns": categorical, "text_columns": text, "missing_values": missing, "duplicate_rows": int(frame.duplicated().sum())}


def analyze_sentiment(frame: pd.DataFrame) -> dict:
    by_name = {_normalized(column): str(column) for column in frame.columns}
    rating_column = next((by_name[name] for name in RATING_NAMES if name in by_name), None)
    if rating_column:
        ratings = pd.to_numeric(frame[rating_column], errors="coerce").dropna()
        if not ratings.empty:
            minimum, maximum, average = float(ratings.min()), float(ratings.max()), float(ratings.mean())
            if minimum >= 1 and maximum <= 5:
                score = (average - 1) / 4 * 100; positive = int((ratings >= 4).sum()); negative = int((ratings <= 2).sum())
            elif minimum >= 0 and maximum <= 10:
                score = average * 10; positive = int((ratings >= 7).sum()); negative = int((ratings <= 4).sum())
            elif maximum > minimum:
                score = (average - minimum) / (maximum - minimum) * 100; positive = int((ratings >= ratings.quantile(.67)).sum()); negative = int((ratings <= ratings.quantile(.33)).sum())
            else:
                return {"available": False, "message": f"Sentiment analysis unavailable — {rating_column} has no usable rating variation.", "distribution": []}
            neutral = int(len(ratings) - positive - negative)
            return _sentiment_result(score, "rating", rating_column, positive, neutral, negative, len(ratings))

    text_column = next((by_name[name] for name in TEXT_SENTIMENT_NAMES if name in by_name), None)
    if text_column:
        values = frame[text_column].dropna().astype(str).map(str.strip)
        values = values[values != ""]
        if not values.empty:
            analyzer = SentimentIntensityAnalyzer()
            compounds = values.map(lambda value: analyzer.polarity_scores(value)["compound"])
            positive = int((compounds >= .05).sum()); negative = int((compounds <= -.05).sum()); neutral = int(len(compounds) - positive - negative)
            score = float(((compounds.mean() + 1) / 2) * 100)
            return _sentiment_result(score, "vader", text_column, positive, neutral, negative, len(compounds))

    return {"available": False, "score": None, "label": None, "method": None, "source_column": None, "sample_count": 0, "distribution": [], "message": "Sentiment analysis unavailable — this dataset does not contain customer feedback, reviews, ratings, or sentiment-related data."}


def _sentiment_result(score: float, method: str, column: str, positive: int, neutral: int, negative: int, count: int) -> dict:
    score = round(max(0, min(100, score)), 1)
    label = "Positive" if score >= 67 else "Neutral" if score >= 40 else "Negative"
    return {"available": True, "score": score, "label": label, "method": method, "source_column": column, "sample_count": count, "distribution": [{"label": "Positive", "value": positive}, {"label": "Neutral", "value": neutral}, {"label": "Negative", "value": negative}], "message": f"{label} sentiment from {count:,} values in {column}."}


def analyze_business_risks(frame: pd.DataFrame) -> list[dict]:
    risks: list[Risk] = []
    clean = frame.copy()
    for column in ("Revenue", "Orders", "Cancelled"):
        if column in clean: clean[column] = pd.to_numeric(clean[column], errors="coerce")
    if "Date" in clean: clean["Date"] = pd.to_datetime(clean["Date"], errors="coerce")
    valid = clean.dropna(subset=[column for column in ("Revenue", "Orders", "Cancelled") if column in clean])
    if valid.empty: return []
    revenue = float(valid["Revenue"].sum()) if "Revenue" in valid else 0

    if "Date" in valid and "Revenue" in valid:
        daily = valid.dropna(subset=["Date"]).groupby("Date")["Revenue"].sum().sort_index()
        if len(daily) >= 2:
            split = max(1, len(daily) // 2); previous = float(daily.iloc[:-split].sum()); current = float(daily.iloc[-split:].sum())
            if previous > 0:
                change = (current - previous) / previous * 100
                if change <= -10:
                    severity = "high" if change <= -20 else "medium"
                    risks.append(Risk("Revenue Risk", severity, "period_revenue_change_percent", round(change, 2), "medium <= -10%; high <= -20%", f"Revenue declined {abs(change):.2f}% between comparable dataset periods.", f"Previous period: {previous:,.2f}; current period: {current:,.2f}.", "Investigate the regions, products, and customers contributing most to the decline."))
            average = float(daily.mean()); deviation = float(daily.std(ddof=0))
            if average > 0 and deviation / average >= .5:
                cv = deviation / average * 100
                risks.append(Risk("Revenue Risk", "medium", "revenue_volatility_percent", round(cv, 2), "medium >= 50%", "Daily revenue is materially unstable.", f"Coefficient of variation: {cv:.2f}% across {len(daily)} reporting days.", "Review outlier days and reduce dependence on irregular transactions."))
            if len(daily) >= 3 and deviation > 0:
                zscores = (daily - average) / deviation
                lows = zscores[zscores <= -2]
                if not lows.empty:
                    date, value = lows.idxmin(), float(daily.loc[lows.idxmin()])
                    risks.append(Risk("Anomaly Risk", "high", "low_revenue_z_score", round(float(lows.min()), 2), "high <= -2 z-score", "An unusually low revenue period was detected.", f"{date.date()}: {value:,.2f}, z-score {float(lows.min()):.2f}.", "Validate the source record and investigate operational events on that date."))

    for column, category in (("Customer", "Customer Concentration Risk"), ("Product", "Product Concentration Risk"), ("Region", "Regional Concentration Risk")):
        if column in valid and revenue > 0:
            grouped = valid.groupby(column, dropna=False)["Revenue"].sum().sort_values(ascending=False)
            if not grouped.empty:
                share = float(grouped.iloc[0] / revenue * 100)
                if share >= 35:
                    severity = "high" if share >= 50 else "medium"
                    risks.append(Risk(category, severity, f"top_{column.lower()}_revenue_share_percent", round(share, 2), "medium >= 35%; high >= 50%", f"Revenue is concentrated in one {column.lower()}.", f"{grouped.index[0]} contributes {share:.2f}% ({float(grouped.iloc[0]):,.2f}) of revenue.", f"Diversify revenue beyond {grouped.index[0]} and monitor concentration monthly."))

    if {"Orders", "Cancelled"}.issubset(valid.columns):
        orders, cancelled = float(valid["Orders"].sum()), float(valid["Cancelled"].sum())
        if orders > 0:
            rate = cancelled / orders * 100
            if rate >= 5:
                severity = "high" if rate >= 10 else "medium"
                risks.append(Risk("Order Risk", severity, "cancellation_rate_percent", round(rate, 2), "medium >= 5%; high >= 10%", "The cancellation rate exceeds the operating threshold.", f"{cancelled:,.0f} cancellations from {orders:,.0f} orders ({rate:.2f}%).", "Segment cancellations by product, region, and customer and address the largest driver."))

    missing = int(frame.isna().sum().sum()); duplicates = int(frame.duplicated().sum())
    affected = missing + duplicates
    if affected:
        ratio = affected / max(1, len(frame)) * 100
        risks.append(Risk("Data Quality Risk", "high" if ratio >= 10 else "medium", "missing_and_duplicate_signals", float(affected), "medium > 0; high >= 10% of rows", "Data quality issues can distort reported metrics.", f"{missing} missing cells and {duplicates} duplicate rows across {len(frame):,} records.", "Correct or explicitly exclude affected records before operational decisions."))
    return [asdict(risk) for risk in sorted(risks, key=lambda item: {"high": 0, "medium": 1, "low": 2}[item.severity])]


def risk_markdown(name: str, risks: list[dict]) -> str:
    if not risks:
        return f"### Risk analysis for **{name}**\n\nNo material risk crossed the configured evidence thresholds. This does not prove the business is risk-free; it means the available columns do not support a flagged risk."
    lines = [f"### Risk analysis for **{name}**", ""]
    for index, risk in enumerate(risks, 1):
        lines.extend([f"**{index}. {risk['severity'].upper()} — {risk['category']}**", f"- Metric: `{risk['metric']}` = **{risk['actual_value']:,.2f}**", f"- Evidence: {risk['evidence']}", f"- Threshold: {risk['threshold']}", f"- Why it matters: {risk['explanation']}", f"- Recommendation: {risk['recommendation']}", ""])
    return "\n".join(lines).strip()

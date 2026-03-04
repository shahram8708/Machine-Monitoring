from datetime import date
from sqlalchemy import func
from app.extensions import db
from app.models.usage_analytics import UsageMetric


SUPPORTED_METRICS = {
    "api_calls",
    "ai_predictions",
    "report_generation",
    "digital_twin_simulation",
}


def track_usage(company_id: int, metric_type: str, increment: int = 1) -> None:
    if metric_type not in SUPPORTED_METRICS:
        return
    today = date.today()
    metric = (
        UsageMetric.query.filter_by(company_id=company_id, metric_type=metric_type, date=today)
        .with_for_update(of=UsageMetric)
        .first()
    )
    if not metric:
        metric = UsageMetric(company_id=company_id, metric_type=metric_type, date=today, count=0)
        db.session.add(metric)
    metric.count += max(1, increment)
    db.session.commit()


def get_company_usage(company_id: int):
    rows = (
        db.session.query(UsageMetric.metric_type, func.sum(UsageMetric.count))
        .filter(UsageMetric.company_id == company_id)
        .group_by(UsageMetric.metric_type)
        .all()
    )
    return {metric: total for metric, total in rows}

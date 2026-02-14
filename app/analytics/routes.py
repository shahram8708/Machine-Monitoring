from datetime import datetime, timedelta, date
from flask import jsonify, render_template, request
from flask_login import current_user, login_required

from app.analytics import analytics_bp
from app.decorators import role_required
from app.models.machine import Machine
from app.security import get_active_company_id
from app.services.analytics_service import (
    get_energy_consumption,
    get_runtime_stats,
    get_temperature_trend,
    get_vibration_trend,
)


def _get_machine_or_404(machine_id: int) -> Machine:
    company_id = get_active_company_id()
    return Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()


def _parse_date(value: str) -> datetime:
    try:
        # Accept both date-only and full ISO strings
        if len(value) == 10:
            return datetime.strptime(value, "%Y-%m-%d")
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _parse_range() -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    default_start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
    default_end = now.replace(hour=23, minute=59, second=59, microsecond=0)

    start_param = request.args.get("start_date")
    end_param = request.args.get("end_date")

    start_dt = _parse_date(start_param) if start_param else default_start
    end_dt = _parse_date(end_param) if end_param else default_end

    if start_dt is None:
        start_dt = default_start
    if end_dt is None:
        end_dt = default_end

    # Normalize to day boundaries for consistency
    start_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dt = end_dt.replace(hour=23, minute=59, second=59, microsecond=0)

    if start_dt > end_dt:
        start_dt, end_dt = end_dt, start_dt

    return start_dt, end_dt


@analytics_bp.route("/<int:machine_id>")
@login_required
@role_required("admin", "manager", "viewer")
def analytics_dashboard(machine_id: int):
    machine = _get_machine_or_404(machine_id)
    start_dt, end_dt = _parse_range()
    return render_template(
        "analytics/dashboard.html",
        machine=machine,
        start_date=start_dt.date(),
        end_date=end_dt.date(),
    )


@analytics_bp.route("/<int:machine_id>/data")
@login_required
@role_required("admin", "manager", "viewer")
def analytics_data(machine_id: int):
    machine = _get_machine_or_404(machine_id)
    start_dt, end_dt = _parse_range()

    temp_series = get_temperature_trend(machine.id, start_dt, end_dt)
    vib_series = get_vibration_trend(machine.id, start_dt, end_dt)
    energy_series = get_energy_consumption(machine.id, start_dt, end_dt)
    runtime = get_runtime_stats(machine.id, start_dt, end_dt)

    return jsonify(
        {
            "machine": {"id": machine.id, "name": machine.machine_name},
            "start_date": start_dt.isoformat(),
            "end_date": end_dt.isoformat(),
            "temperature": temp_series,
            "vibration": vib_series,
            "energy": energy_series,
            "runtime": runtime,
        }
    )

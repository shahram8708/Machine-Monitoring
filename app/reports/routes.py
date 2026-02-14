from __future__ import annotations

from datetime import datetime, timedelta
from io import BytesIO

from flask import render_template, send_file
from flask_login import login_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func

from app.decorators import role_required
from app.models.ai_analysis import AiAnalysis
from app.models.alert import Alert
from app.models.machine import Machine
from app.models.machine_data import MachineData
from app.security import get_active_company_id
from app.services.analytics_service import get_runtime_stats
from . import reports_bp


def _get_machine_or_404(machine_id: int) -> Machine:
    company_id = get_active_company_id()
    return Machine.query.filter_by(id=machine_id, company_id=company_id).first_or_404()


def _metric_window(days: int) -> tuple[datetime, datetime]:
    end_dt = datetime.utcnow()
    start_dt = end_dt - timedelta(days=days)
    return start_dt, end_dt


def _fetch_metrics(machine: Machine, start_dt: datetime, end_dt: datetime) -> dict:
    runtime = get_runtime_stats(machine.id, start_dt, end_dt)
    energy_series = (
        MachineData.query.filter_by(machine_id=machine.id)
        .filter(MachineData.timestamp >= start_dt, MachineData.timestamp <= end_dt)
        .order_by(MachineData.timestamp.asc())
        .all()
    )
    total_energy_kwh = 0.0
    for idx, record in enumerate(energy_series):
        next_ts = energy_series[idx + 1].timestamp if idx + 1 < len(energy_series) else None
        duration = (next_ts - record.timestamp).total_seconds() if next_ts else 60.0
        if record.voltage and record.current:
            total_energy_kwh += (record.voltage * record.current * duration) / 3_600_000

    avg_temp = (
        MachineData.query.with_entities(func.avg(MachineData.temperature))
        .filter_by(machine_id=machine.id)
        .filter(MachineData.timestamp >= start_dt, MachineData.timestamp <= end_dt)
        .scalar()
    )
    latest_ai = (
        AiAnalysis.query.filter_by(machine_id=machine.id, status="completed")
        .order_by(AiAnalysis.created_at.desc())
        .first()
    )
    alerts_q = Alert.query.filter_by(machine_id=machine.id).filter(Alert.created_at >= start_dt, Alert.created_at <= end_dt)
    alert_count = alerts_q.count()
    unresolved = alerts_q.filter_by(is_resolved=False).count()

    return {
        "runtime": runtime,
        "energy_kwh": round(total_energy_kwh, 3),
        "avg_temp": round(avg_temp or 0.0, 2),
        "health": latest_ai.health_score if latest_ai else None,
        "risk": latest_ai.risk_level if latest_ai else None,
        "alert_count": alert_count,
        "unresolved": unresolved,
    }


def _render_pdf(machine: Machine, title: str, metrics: dict, start_dt: datetime, end_dt: datetime) -> BytesIO:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph(title, styles["Title"]))
    subtitle = f"Machine: {machine.machine_name} • Company: {machine.company.company_name}"
    elements.append(Paragraph(subtitle, styles["Heading3"]))
    window = f"Period: {start_dt.strftime('%Y-%m-%d %H:%M')} to {end_dt.strftime('%Y-%m-%d %H:%M')} UTC"
    elements.append(Paragraph(window, styles["Normal"]))
    elements.append(Spacer(1, 12))

    table_data = [
        ["Metric", "Value"],
        ["Machine Type", machine.machine_type],
        ["Location", machine.location or "-"],
        ["Runtime (hrs)", f"{metrics['runtime'].get('running_hours', 0):.2f}"],
        ["Idle (hrs)", f"{metrics['runtime'].get('idle_hours', 0):.2f}"],
        ["Energy (kWh)", f"{metrics['energy_kwh']:.3f}"],
        ["Avg Temperature (°C)", f"{metrics['avg_temp']:.2f}"],
        ["AI Health Score", metrics['health'] if metrics['health'] is not None else "—"],
        ["AI Risk", metrics['risk'] if metrics['risk'] else "—"],
        ["Alerts (period)", str(metrics['alert_count'])],
        ["Unresolved Alerts", str(metrics['unresolved'])],
    ]
    table = Table(table_data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 12))

    alerts_summary = (
        Alert.query.filter_by(machine_id=machine.id)
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )
    if alerts_summary:
        elements.append(Paragraph("Recent Alerts", styles["Heading4"]))
        alert_rows = [["Time", "Severity", "Message"]]
        for alert in alerts_summary:
            alert_rows.append([
                alert.created_at.strftime("%Y-%m-%d %H:%M"),
                alert.severity.title(),
                alert.message,
            ])
        alert_table = Table(alert_rows, hAlign="LEFT")
        alert_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey), ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey), ("BOX", (0, 0), (-1, -1), 0.5, colors.grey)]))
        elements.append(alert_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer


def _send_report(machine: Machine, report_name: str, days: int):
    start_dt, end_dt = _metric_window(days)
    metrics = _fetch_metrics(machine, start_dt, end_dt)
    title = f"{report_name} Report"
    pdf_buffer = _render_pdf(machine, title, metrics, start_dt, end_dt)
    filename = f"{machine.machine_name}-{report_name.lower().replace(' ', '-')}.pdf"
    return send_file(pdf_buffer, mimetype="application/pdf", as_attachment=True, download_name=filename)


@reports_bp.route("/")
@login_required
@role_required("admin", "manager", "viewer")
def reports_index():
    company_id = get_active_company_id()
    machines = Machine.query.filter_by(company_id=company_id).order_by(Machine.machine_name).all()
    return render_template("reports/index.html", machines=machines)


@reports_bp.route("/<int:machine_id>/daily")
@login_required
@role_required("admin", "manager", "viewer")
def daily_report(machine_id: int):
    machine = _get_machine_or_404(machine_id)
    return _send_report(machine, "Daily", 1)


@reports_bp.route("/<int:machine_id>/weekly")
@login_required
@role_required("admin", "manager", "viewer")
def weekly_report(machine_id: int):
    machine = _get_machine_or_404(machine_id)
    return _send_report(machine, "Weekly", 7)


@reports_bp.route("/<int:machine_id>/monthly")
@login_required
@role_required("admin", "manager", "viewer")
def monthly_report(machine_id: int):
    machine = _get_machine_or_404(machine_id)
    return _send_report(machine, "Monthly", 30)


@reports_bp.route("/<int:machine_id>/energy")
@login_required
@role_required("admin", "manager", "viewer")
def energy_report(machine_id: int):
    machine = _get_machine_or_404(machine_id)
    return _send_report(machine, "Energy Usage", 30)

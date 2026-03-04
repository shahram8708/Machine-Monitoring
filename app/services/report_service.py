from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from io import BytesIO
from typing import Dict, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func

from app.extensions import db
from app.models import (
    AIPrediction,
    ExecutiveReport,
    Machine,
    MachineHealthScore,
    MachineKPI,
)
from app.services.financial_service import cost_to_failure
from app.services.gemini_service import generate_gemini_response
from app.services.spare_parts_service import recommendation_summary
from app.services.workforce_service import analytics_overview
from app.services.esg_service import esg_summary
from app.ai.prompt_templates import executive_summary_prompt


REPORT_DIR = os.path.join(os.getcwd(), "generated_reports")


def _kpi_summary(company_id: int) -> Dict[str, float]:
    avg_oee = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.oee))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    avg_availability = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.availability))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    avg_performance = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.performance))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    avg_quality = (
        MachineKPI.query.with_entities(func.avg(MachineKPI.quality))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    return {
        "oee": round(avg_oee, 3),
        "availability": round(avg_availability, 3),
        "performance": round(avg_performance, 3),
        "quality": round(avg_quality, 3),
    }


def _health_overview(company_id: int) -> Dict[str, float]:
    avg_health = (
        MachineHealthScore.query.with_entities(func.avg(MachineHealthScore.health_score))
        .join(Machine)
        .filter(Machine.company_id == company_id)
        .scalar()
    ) or 0
    critical = (
        MachineHealthScore.query.join(Machine)
        .filter(Machine.company_id == company_id, MachineHealthScore.risk_level == "CRITICAL")
        .count()
    )
    return {"avg_health": round(avg_health, 2), "critical_machines": critical}


def _failure_highlights(company_id: int) -> List[dict]:
    recent = (
        AIPrediction.query.filter_by(company_id=company_id)
        .order_by(AIPrediction.created_at.desc())
        .all()
    )
    return [
        {
            "machine_id": p.machine_id,
            "risk_level": p.risk_level,
            "failure_probability": p.failure_probability,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p in recent
    ]


def _build_ai_summary(company_id: int, sections: Dict[str, object]) -> Dict[str, object]:
    try:
        return generate_gemini_response(executive_summary_prompt, sections)
    except Exception:  # noqa: BLE001
        return {
            "executive_summary": "AI unavailable; showing synthesized snapshot.",
            "strategic_risks": ["Data insufficient", "AI offline"],
            "recommended_actions": ["Review critical machines", "Validate spare stock"],
            "confidence": 0,
        }


def _table(data: List[List[str]]):
    table = Table(data, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    return table


def _render_pdf(company_name: str, payload: Dict[str, object]) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=1.5 * cm, rightMargin=1.5 * cm)
    styles = getSampleStyleSheet()

    elements = []
    elements.append(Paragraph("Executive AI Report", styles["Title"]))
    elements.append(Paragraph(company_name, styles["Heading2"]))
    elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}", styles["Normal"]))
    elements.append(Spacer(1, 12))

    kpi = payload["kpi_summary"]
    elements.append(Paragraph("Company KPI Summary", styles["Heading3"]))
    elements.append(
        _table(
            [
                ["Metric", "Value"],
                ["OEE", str(kpi["oee"])],
                ["Availability", str(kpi["availability"])],
                ["Performance", str(kpi["performance"])],
                ["Quality", str(kpi["quality"])],
            ]
        )
    )
    elements.append(Spacer(1, 10))

    health = payload["health_overview"]
    elements.append(Paragraph("Health Overview", styles["Heading3"]))
    elements.append(
        _table(
            [
                ["Average Health", str(health["avg_health"])],
                ["Critical Machines", str(health["critical_machines"])],
            ]
        )
    )
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Failure Prediction Highlights", styles["Heading3"]))
    failure_rows = [["Machine", "Risk", "Failure %", "Timestamp"]]
    for rec in payload.get("failure_highlights", []):
        failure_rows.append([
            str(rec["machine_id"]),
            rec.get("risk_level", "-"),
            str(rec.get("failure_probability", "-")),
            rec.get("created_at", "-"),
        ])
    elements.append(_table(failure_rows))
    elements.append(Spacer(1, 10))

    fin = payload["financial"]
    elements.append(Paragraph("Downtime Cost Projection", styles["Heading3"]))
    elements.append(_table([["Projected Downtime Cost", f"${fin['projected_downtime_cost']}",], ["Projected Revenue Loss", f"${fin['projected_revenue_loss']}",], ["Total Risk Exposure", f"${fin['total_risk_exposure']}",]]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Spare Parts Recommendation", styles["Heading3"]))
    sp = payload["spares"]
    elements.append(_table([["Total Items", str(sp["total_items"])], ["At Risk", str(sp["at_risk"])], ["Avg Lead Time (days)", str(sp["avg_lead_time_days"])]]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("Workforce Efficiency", styles["Heading3"]))
    wf = payload["workforce"]
    elements.append(_table([["Open Tasks", str(wf["open_tasks"])], ["Delayed Tasks", str(wf["delayed_tasks"])], ["Top Technician", wf.get("top_technician", "-")]]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("ESG & Energy", styles["Heading3"]))
    esg = payload["esg"]
    elements.append(_table([["Total Energy (kWh)", str(esg.get("total_energy_kwh", 0))], ["Sustainability Score", str(esg.get("sustainability_score", 0))], ["Carbon Proxy (kg)", str(esg.get("carbon_proxy_kg", 0))]]))
    elements.append(Spacer(1, 10))

    exec_ai = payload.get("executive_ai", {})
    elements.append(Paragraph("Executive AI Summary", styles["Heading3"]))
    elements.append(Paragraph(exec_ai.get("executive_summary", ""), styles["Normal"]))
    if exec_ai.get("strategic_risks"):
        elements.append(Paragraph("Strategic Risks", styles["Heading4"]))
        for r in exec_ai.get("strategic_risks", []):
            elements.append(Paragraph(f"- {r}", styles["Normal"]))
    if exec_ai.get("recommended_actions"):
        elements.append(Paragraph("Recommended Actions", styles["Heading4"]))
        for a in exec_ai.get("recommended_actions", []):
            elements.append(Paragraph(f"- {a}", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def generate_executive_report(company_id: int, user_id: int) -> Dict[str, object]:
    company_machines = Machine.query.filter_by(company_id=company_id).all()
    company_name = company_machines[0].company.company_name if company_machines else "Company"

    kpi = _kpi_summary(company_id)
    health = _health_overview(company_id)
    failure_highlights = _failure_highlights(company_id)
    spares = recommendation_summary(company_id)

    # Financial aggregate using first machine as proxy
    fin = {"projected_downtime_cost": 0, "projected_revenue_loss": 0, "total_risk_exposure": 0, "confidence": 0}
    if company_machines:
        fin = cost_to_failure(company_machines[0].id, company_id)

    wf = analytics_overview(company_id)
    top_tech = wf.get("ranking", [{}])[0] if wf.get("ranking") else {}
    wf["top_technician"] = top_tech.get("technician_name")

    esg = esg_summary(company_machines[0].id, company_id) if company_machines else {"sustainability_score": 0, "carbon_proxy_kg": 0, "energy_trend": {"total_energy_kwh": 0}}

    sections = {
        "kpi_summary": kpi,
        "health_overview": health,
        "failure_highlights": failure_highlights,
        "financial": fin,
        "spares": spares,
        "workforce": wf,
        "esg": esg,
    }
    exec_ai = _build_ai_summary(company_id, sections)
    sections["executive_ai"] = exec_ai

    pdf_bytes = _render_pdf(company_name, sections)

    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = f"executive-report-{uuid.uuid4().hex}.pdf"
    path = os.path.join(REPORT_DIR, filename)
    with open(path, "wb") as f:
        f.write(pdf_bytes)

    report = ExecutiveReport(company_id=company_id, user_id=user_id, report_path=path, summary_json=sections)
    db.session.add(report)
    db.session.commit()

    return {"report_id": report.id, "path": path, "summary": exec_ai}


def get_report(report_id: int, company_id: int) -> ExecutiveReport:
    return ExecutiveReport.query.filter_by(id=report_id, company_id=company_id).first_or_404()

from datetime import datetime, timedelta
from app.extensions import scheduler, db
from app.models.machine import Machine
from app.models.audit_log import AuditLog
from app.services.analytics_service import run_nightly_aggregation
from app.services.alert_service import escalate_open_alerts
from app.services.predictive_service import run_scheduled_predictions


def _run_alert_escalation(app) -> None:
    with app.app_context():
        escalate_open_alerts()


def _mark_offline_machines(app) -> None:
    with app.app_context():
        threshold = datetime.utcnow() - timedelta(minutes=2)
        stale = (
            Machine.query.filter(Machine.last_seen.isnot(None))
            .filter(Machine.last_seen < threshold)
            .filter(Machine.status != "offline")
            .all()
        )
        if not stale:
            return

        for machine in stale:
            old_status = machine.status
            machine.status = "offline"
            db.session.add(
                AuditLog(
                    user_id=None,
                    company_id=machine.company_id,
                    plant_id=machine.plant_id,
                    action="machine_offline",
                    action_type="status_change",
                    entity_type="machine",
                    entity_id=machine.id,
                    old_value={"status": old_status},
                    previous_value={"status": old_status},
                    new_value={"status": "offline", "alert": "Machine communication lost"},
                    timestamp=datetime.utcnow(),
                    ip_address=None,
                )
            )
        db.session.commit()


def _run_predictive_refresh(app) -> None:
    with app.app_context():
        run_scheduled_predictions()


def init_scheduler(app) -> None:
    if scheduler.running:
        return

    scheduler.configure(timezone="UTC")
    scheduler.add_job(
        func=lambda: _mark_offline_machines(app),
        trigger="interval",
        minutes=1,
        id="offline_monitor",
        replace_existing=True,
    )
    scheduler.add_job(
        func=lambda: run_nightly_aggregation(app),
        trigger="cron",
        hour=2,
        minute=15,
        id="analytics_aggregation",
        replace_existing=True,
    )
    scheduler.add_job(
        func=lambda: _run_alert_escalation(app),
        trigger="interval",
        minutes=1,
        id="alert_escalation",
        replace_existing=True,
    )
    scheduler.add_job(
        func=lambda: _run_predictive_refresh(app),
        trigger="interval",
        minutes=30,
        id="predictive_refresh",
        replace_existing=True,
    )
    scheduler.start()

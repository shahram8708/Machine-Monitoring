import logging
import time
from queue import Queue
from threading import Thread
from typing import Optional

from app.extensions import db
from app.models.ai_analysis import AiAnalysis
from app.models.machine_data import MachineData
from .gemini_engine import run_ai_analysis

logger = logging.getLogger(__name__)

_job_queue: Queue[dict] = Queue()
_worker_thread: Optional[Thread] = None
_worker_started = False


def init_ai_worker(app) -> None:
    global _worker_thread, _worker_started
    if _worker_started:
        return

    def _worker():
        with app.app_context():
            while True:
                job = _job_queue.get()
                if job is None:
                    _job_queue.task_done()
                    break
                try:
                    _process_job(job)
                finally:
                    _job_queue.task_done()

    _worker_thread = Thread(target=_worker, name="ai-analysis-worker", daemon=True)
    _worker_thread.start()
    _worker_started = True


def enqueue_ai_job(machine_data_id: int) -> None:
    if not _worker_started:
        logger.warning("AI worker not started; skipping enqueue")
        return
    try:
        _create_pending_if_needed(machine_data_id)
    except Exception:  # noqa: BLE001
        logger.exception("Failed to create pending AI analysis record")
    _job_queue.put({"machine_data_id": machine_data_id})


def _get_or_create_pending(machine_data: MachineData) -> AiAnalysis:
    record = (
        AiAnalysis.query.filter_by(machine_id=machine_data.machine_id, timestamp=machine_data.timestamp)
        .order_by(AiAnalysis.created_at.desc())
        .first()
    )
    if record:
        record.status = "pending"
        db.session.add(record)
        db.session.commit()
        return record

    record = AiAnalysis(
        machine_id=machine_data.machine_id,
        timestamp=machine_data.timestamp,
        status="pending",
    )
    db.session.add(record)
    db.session.commit()
    return record


def _create_pending_if_needed(machine_data_id: int) -> None:
    data_point = MachineData.query.get(machine_data_id)
    if not data_point:
        return
    _get_or_create_pending(data_point)


def _process_job(job: dict) -> None:
    machine_data_id = job.get("machine_data_id")
    data_point = MachineData.query.get(machine_data_id)
    if not data_point:
        return

    analysis = _get_or_create_pending(data_point)
    analysis_id = analysis.id
    max_attempts = 3

    for attempt in range(1, max_attempts + 1):
        try:
            result = run_ai_analysis(data_point)
            analysis.health_score = result["health_score"]
            analysis.risk_level = result["risk_level"]
            analysis.anomaly = result["anomaly"]
            analysis.maintenance_suggestion = result.get("maintenance_suggestion")
            analysis.explanation = result.get("explanation")
            analysis.status = "completed"
            db.session.add(analysis)
            db.session.commit()
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("AI analysis failed on attempt %s: %s", attempt, exc)
            db.session.rollback()
            analysis = AiAnalysis.query.get(analysis_id)
            if attempt >= max_attempts:
                if not analysis:
                    return
                analysis.status = "failed"
                analysis.explanation = (analysis.explanation or "") + f"\nAI error: {exc}"
                db.session.add(analysis)
                db.session.commit()
                return
            time.sleep(2 * attempt)


def shutdown_worker():
    if _worker_started:
        _job_queue.put(None)
        if _worker_thread:
            _worker_thread.join(timeout=2)

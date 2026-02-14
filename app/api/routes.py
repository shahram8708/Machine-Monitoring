from datetime import datetime
from flask import jsonify, request
from app.extensions import db, csrf
from app.models.machine import Machine
from app.models.machine_data import MachineData
from app.ai.worker import enqueue_ai_job
from app.services.alert_service import evaluate_alerts_for_datapoint
from . import api_bp


def _error(message: str, status_code: int):
    return jsonify({"status": "error", "message": message}), status_code


def _get_machine_from_token():
    token = request.headers.get("X-API-KEY")
    if not token:
        return None, _error("API token missing.", 401)

    machine = Machine.query.filter_by(api_token=token).first()
    if not machine:
        return None, _error("Invalid API token.", 401)
    return machine, None


def _parse_timestamp(value):
    if not value:
        return datetime.utcnow()
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _parse_float(field_name: str, value, errors):
    if value is None:
        errors.append(f"{field_name} is required.")
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        errors.append(f"{field_name} must be numeric.")
        return None


@api_bp.route("/data-ingest", methods=["POST"])
@csrf.exempt
def data_ingest():
    machine, error_response = _get_machine_from_token()
    if error_response:
        return error_response

    payload = request.get_json(silent=True) or {}
    machine_id = payload.get("machine_id")
    if machine_id != machine.id:
        return _error("Machine token mismatch.", 401)

    ts = _parse_timestamp(payload.get("timestamp"))
    if ts is None:
        return _error("Invalid timestamp format. Use ISO 8601.", 400)

    errors = []
    temperature = _parse_float("temperature", payload.get("temperature"), errors)
    vibration = _parse_float("vibration", payload.get("vibration"), errors)
    current_val = _parse_float("current", payload.get("current"), errors)
    voltage = _parse_float("voltage", payload.get("voltage"), errors)
    pressure = _parse_float("pressure", payload.get("pressure"), errors)
    humidity = _parse_float("humidity", payload.get("humidity"), errors)
    speed = _parse_float("speed", payload.get("speed"), errors)

    running_status = payload.get("running_status")
    if running_status is None or not isinstance(running_status, bool):
        errors.append("running_status must be boolean.")

    if errors:
        return _error(", ".join(errors), 400)

    now = datetime.utcnow()
    data_point = MachineData(
        machine_id=machine.id,
        timestamp=ts,
        temperature=temperature,
        vibration=vibration,
        current=current_val,
        voltage=voltage,
        pressure=pressure,
        humidity=humidity,
        speed=speed,
        running_status=running_status,
        created_at=now,
    )
    machine.last_seen = now
    machine.status = "running" if running_status else "idle"

    db.session.add(data_point)
    db.session.commit()

    try:
        evaluate_alerts_for_datapoint(data_point)
    except Exception:  # noqa: BLE001
        # Alerts should not block ingestion
        pass

    enqueue_ai_job(data_point.id)

    return jsonify({"status": "success", "message": "data stored"}), 201


@api_bp.route("/heartbeat", methods=["POST"])
@csrf.exempt
def heartbeat():
    machine, error_response = _get_machine_from_token()
    if error_response:
        return error_response

    now = datetime.utcnow()
    machine.last_seen = now
    if machine.status == "offline":
        machine.status = "idle"
    db.session.commit()

    return jsonify({"status": "success", "message": "heartbeat received", "last_seen": now.isoformat()}), 200

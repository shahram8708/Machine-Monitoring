import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict

from google import genai
from google.genai import types

from app.models.machine_data import MachineData


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

grounding_tool = types.Tool(
    google_search=types.GoogleSearch()
)

config = types.GenerateContentConfig(
    tools=[grounding_tool]
)

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


def _safe_json_extract(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json|```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
    cleaned = re.sub(r"^```|```$", "", cleaned, flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _coerce_response(data: Dict[str, Any]) -> Dict[str, Any]:
    risk = str(data.get("risk_level", "")).strip().lower()
    if risk not in {"low", "medium", "high"}:
        risk = "medium"
    anomaly = bool(data.get("anomaly", False))
    try:
        score = float(data.get("health_score", 0))
    except (TypeError, ValueError):
        score = 0.0
    score = max(0.0, min(100.0, score))
    return {
        "health_score": score,
        "risk_level": risk,
        "anomaly": anomaly,
        "maintenance_suggestion": data.get("maintenance_suggestion", "No suggestion provided."),
        "explanation": data.get("explanation", ""),
    }


def _history_summary(machine_data: MachineData) -> str:
    window_start = machine_data.timestamp - timedelta(hours=24)
    records = (
        MachineData.query.filter_by(machine_id=machine_data.machine_id)
        .filter(MachineData.timestamp >= window_start, MachineData.timestamp <= machine_data.timestamp)
        .order_by(MachineData.timestamp.asc())
        .limit(200)
        .all()
    )
    if not records:
        return "No historical context available in the last 24 hours."

    def _agg(field: str):
        values = [getattr(r, field) for r in records if getattr(r, field) is not None]
        if not values:
            return None, None, None
        return sum(values) / len(values), min(values), max(values)

    temp_avg, temp_min, temp_max = _agg("temperature")
    vib_avg, vib_min, vib_max = _agg("vibration")
    curr_avg, curr_min, curr_max = _agg("current")
    volt_avg, volt_min, volt_max = _agg("voltage")
    speed_avg, speed_min, speed_max = _agg("speed")

    lines = [
        f"Time window: {window_start.isoformat()} to {machine_data.timestamp.isoformat()} UTC",
        "Averages (min/max) over window:",
    ]
    if temp_avg is not None:
        lines.append(f"- Temperature: avg {temp_avg:.2f}°C (min {temp_min:.2f}, max {temp_max:.2f})")
    if vib_avg is not None:
        lines.append(f"- Vibration: avg {vib_avg:.3f} mm/s (min {vib_min:.3f}, max {vib_max:.3f})")
    if curr_avg is not None and volt_avg is not None:
        lines.append(f"- Electrical: current avg {curr_avg:.2f} A, voltage avg {volt_avg:.1f} V")
    if speed_avg is not None:
        lines.append(f"- Speed: avg {speed_avg:.1f} rpm (min {speed_min:.1f}, max {speed_max:.1f})")
    return "\n".join(lines)


def _build_prompt(machine_data: MachineData) -> str:
    snapshot = {
        "timestamp": machine_data.timestamp.isoformat(),
        "temperature": machine_data.temperature,
        "vibration": machine_data.vibration,
        "current": machine_data.current,
        "voltage": machine_data.voltage,
        "speed": machine_data.speed,
        "pressure": machine_data.pressure,
        "humidity": machine_data.humidity,
        "running_status": machine_data.running_status,
    }
    summary = _history_summary(machine_data)
    return (
        "You are an industrial predictive maintenance assistant. Analyze the machine sensor snapshot below "
        "and provide maintenance insights. Use grounded reasoning with Google Search tool only if needed.\n\n"
        f"Sensor snapshot (latest reading):\n{json.dumps(snapshot, indent=2)}\n\n"
        f"Historical behavior summary (last 24h):\n{summary}\n\n"
        "Return STRICT JSON ONLY with the following shape and nothing else:\n"
        "{\n"
        "  \"health_score\": number between 0 and 100,\n"
        "  \"risk_level\": \"low\"|\"medium\"|\"high\",\n"
        "  \"anomaly\": true or false,\n"
        "  \"maintenance_suggestion\": string,\n"
        "  \"explanation\": string\n"
        "}\n"
        "Do not add prose outside the JSON."
    )


def run_ai_analysis(machine_data: MachineData) -> Dict[str, Any]:
    prompt = _build_prompt(machine_data)
    response = client.models.generate_content(
        model=MODEL_NAME,
        config=config,
        contents=[types.Content(role="user", parts=[types.Part.from_text(prompt)])],
    )
    text = getattr(response, "text", "") or ""
    parsed = _safe_json_extract(text)
    return _coerce_response(parsed)

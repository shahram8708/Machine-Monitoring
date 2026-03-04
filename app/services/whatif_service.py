from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

from google import genai
from google.genai import types

from app.ai.prompt_templates import what_if_analysis_prompt
from app.models.digital_twin import DigitalTwin

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def _default_payload(message: str = "Analysis unavailable") -> Dict[str, Any]:
    return {
        "strategic_risk_assessment": message,
        "long_term_impact": "",
        "cost_impact_estimation": "",
        "recommended_action": "",
        "confidence": 0,
    }


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


def _validate_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "strategic_risk_assessment": str(data.get("strategic_risk_assessment", "")).strip(),
        "long_term_impact": str(data.get("long_term_impact", "")).strip(),
        "cost_impact_estimation": str(data.get("cost_impact_estimation", "")).strip(),
        "recommended_action": str(data.get("recommended_action", "")).strip(),
        "confidence": float(data.get("confidence", 0) or 0),
    }


def run_what_if_analysis(twin: DigitalTwin, simulation_result: Dict[str, Any]) -> Dict[str, Any]:
    summary = {
        "baseline": {
            "oee": twin.baseline_oee,
            "health_score": twin.baseline_health_score,
            "failure_probability": twin.baseline_failure_probability,
            "energy_efficiency": twin.baseline_energy_efficiency,
            "degradation_rate": twin.degradation_rate,
        },
        "simulation": {
            "simulated_oee": simulation_result.get("simulated_oee"),
            "simulated_health_score": simulation_result.get("simulated_health_score"),
            "simulated_failure_probability": simulation_result.get("simulated_failure_probability"),
            "simulated_energy_efficiency": simulation_result.get("simulated_energy_efficiency"),
            "risk_delta": simulation_result.get("risk_delta"),
            "impact_level": simulation_result.get("impact_level"),
        },
    }

    try:
        prompt = what_if_analysis_prompt.replace(
            "{data}", json.dumps(summary, ensure_ascii=True, sort_keys=True, indent=2)
        )
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[types.Content(role="user", parts=[types.Part(text=prompt)])],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw_text = getattr(response, "text", "") or ""
        parsed = _safe_json_extract(raw_text)
        return _validate_payload(parsed)
    except Exception as exc:  # noqa: BLE001
        # Never bubble AI failures to the route; return a graceful default instead.
        fallback = _default_payload(message=f"Analysis unavailable: {exc}")
        return _validate_payload(fallback)

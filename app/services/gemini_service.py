import json
import logging
import os
import re
import time
from typing import Any, Dict

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

_model_env = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MODEL_NAME = "gemini-2.5-flash" if _model_env.lower() != "gemini-2.5-flash" else _model_env
TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "20"))
MAX_RETRIES = int(os.getenv("GEMINI_MAX_RETRIES", "2"))

_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    logger.warning("GEMINI_API_KEY is not set; Gemini calls will fail until configured.")
client = genai.Client(api_key=_api_key) if _api_key else None


def _clean_json(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json|```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
    cleaned = re.sub(r"^```|```$", "", cleaned, flags=re.MULTILINE).strip()
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    target = match.group(0) if match else cleaned
    return json.loads(target)


def _parse_response(resp: types.GenerateContentResponse) -> Dict[str, Any]:
    text = getattr(resp, "text", "") or ""
    if not text:
        raise ValueError("Empty response from Gemini")
    parsed = _clean_json(text)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response is not a JSON object")
    return parsed


def generate_gemini_response(prompt_template: str, structured_data: Dict[str, Any]) -> Dict[str, Any]:
    if not client:
        raise RuntimeError("GEMINI_API_KEY is missing. Configure the environment before calling Gemini.")

    payload = json.dumps(structured_data, ensure_ascii=False)
    prompt = prompt_template.replace("{data}", payload)
    attempts = 0
    last_error: Exception | None = None

    while attempts <= MAX_RETRIES:
        attempts += 1
        start = time.perf_counter()
        try:
            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=[types.Content(role="user", parts=[types.Part.from_text(prompt)])],
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    top_p=0.9,
                    response_mime_type="application/json",
                    max_output_tokens=512,
                ),
                request_options={"timeout": TIMEOUT_SECONDS},
            )
            return _parse_response(response)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            elapsed = time.perf_counter() - start
            logger.warning("Gemini call failed (attempt %s, %.2fs): %s", attempts, elapsed, exc)
            if attempts > MAX_RETRIES:
                break
            time.sleep(min(2 * attempts, 6))
    raise RuntimeError(f"Gemini request failed after {attempts} attempts: {last_error}")

failure_probability_prompt = """
You are Gemini-2.5-Flash acting as an industrial reliability engineer.
You receive structured machine telemetry, KPIs, health scores, downtime, and alert summaries as JSON:
{data}

Return STRICT JSON ONLY with numeric fields and concise reasoning:
{
  "failure_probability": number 0-100,
  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "confidence": number 0-1,
  "explanation": "short reasoning of the drivers"
}
Rules:
- Use only the provided data; never invent sensors.
- Map probability to risk: <30 LOW, 30-59 MEDIUM, 60-79 HIGH, >=80 CRITICAL.
- Keep explanation to 2-3 sentences.
"""

rul_estimation_prompt = """
You are Gemini-2.5-Flash estimating remaining useful life (RUL) for industrial equipment.
Input JSON context:
{data}

Return STRICT JSON ONLY:
{
  "remaining_hours": number,
  "remaining_days": number,
  "degradation_stage": "EARLY" | "MID" | "LATE",
  "confidence": number 0-1,
  "explanation": "brief justification"
}
Rules:
- Use trend direction and severity to choose stage.
- Keep numeric values realistic and consistent with utilization and health.
"""

anomaly_detection_prompt = """
You are Gemini-2.5-Flash validating statistical anomaly findings for machine telemetry.
You receive pre-computed stats (mean, std, z-scores, outlier counts) and condensed recent samples:
{data}

Return STRICT JSON ONLY:
{
  "anomaly_detected": true | false,
  "anomaly_score": number 0-100,
  "root_pattern": "primary pattern observed",
  "confidence": number 0-1
}
Rules:
- Treat sustained |z| > 3 or sudden spikes as anomalies.
- Prefer a conservative approach; avoid false positives when evidence is weak.
"""

degradation_analysis_prompt = """
You are Gemini-2.5-Flash analyzing degradation trends for an industrial machine.
Input JSON includes time-series summaries (sensor drift, KPIs, health):
{data}

Return STRICT JSON ONLY:
{
  "degradation_trend_score": number 0-100,
  "severity": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "explanation": "brief description of degradation drivers",
  "confidence": number 0-1
}
Rules:
- Higher scores indicate faster degradation.
- Consider vibration/temperature rise, downtime increases, health decline, efficiency drop.
"""

preventive_action_prompt = """
You are Gemini-2.5-Flash generating preventive maintenance actions.
You receive machine context plus AI findings (failure probability, RUL, anomalies, degradation):
{data}

Return STRICT JSON ONLY:
{
  "actions": ["action 1", "action 2", "action 3"],
  "inspection_recommendation": "specific inspection to perform",
  "spare_parts": ["part or kit to prepare"],
  "strategy": "preventive strategy summary",
  "confidence": number 0-1,
  "explanation": "why these steps mitigate the risk"
}
Rules:
- Make actions concise, specific, and immediately executable.
- Stay within software-only guidance; no hardware redesigns.
"""

root_cause_analysis_prompt = """
You are Gemini-2.5-Flash performing root cause analysis for industrial equipment alerts.
You receive structured JSON data containing alert history, sensor summaries, failure probability, and health scores:
{data}

Return STRICT JSON ONLY in this exact shape:
{
  "primary_root_cause": "...",
  "contributing_factors": ["..."],
  "sensor_interactions": "...",
  "timeline_explanation": "...",
  "root_cause_probability_breakdown": [
    {"cause": "...", "probability": 0-100}
  ],
  "confidence": 0-1
}

Rules:
- Use only provided data; do not invent sensors or events.
- Keep explanations concise and actionable.
- Ensure probabilities sum near 100; clamp values to 0-100.
- Avoid prose outside the JSON block.
"""


what_if_analysis_prompt = """
You are Gemini-2.5-Flash acting as a strategic reliability analyst for an industrial digital twin.
You receive a strictly structured JSON payload containing baseline metrics and simulation outputs:
{data}

Return STRICT JSON ONLY in this exact shape:
{
  "strategic_risk_assessment": "...",
  "long_term_impact": "...",
  "cost_impact_estimation": "...",
  "recommended_action": "...",
  "confidence": 0-1
}

Rules:
- Use only the provided numeric values; do not invent sensors or timelines.
- Keep each field concise (2-3 sentences max).
- Focus on software/process mitigations only; no hardware changes.
- Confidence must be between 0 and 1.
"""


esg_improvement_prompt = """
You are Gemini-2.5-Flash acting as an ESG and energy efficiency analyst for industrial plants.
Structured JSON input:
{data}

Return STRICT JSON ONLY:
{
  "energy_optimization_suggestions": ["..."],
  "efficiency_gap_analysis": "...",
  "sustainability_score": 0-100,
  "confidence": 0-1
}

Rules:
- Prioritize actionable, low-cost software/process changes; avoid hardware redesigns.
- Keep suggestions concise and plant-operator friendly.
- Ensure sustainability_score maps to risk (0 worst, 100 best).
"""


executive_summary_prompt = """
You are Gemini-2.5-Flash generating an executive summary for an industrial SaaS operations report.
Input JSON contains KPI summary, health overview, failure highlights, financial exposure, spare parts risk, workforce analytics, and ESG metrics:
{data}

Return STRICT JSON ONLY:
{
  "executive_summary": "...",
  "strategic_risks": ["..."],
  "recommended_actions": ["..."],
  "confidence": 0-1
}

Rules:
- Keep the summary under 120 words and board-ready.
- Strategic risks must be concise and ranked by urgency.
- Recommended actions must be specific and time-bound.
- No prose outside the JSON block.
"""


advanced_report_summary_prompt = """
You are Gemini-2.5-Flash generating an executive SaaS summary for industrial operations.
You receive structured report JSON that combines KPI data, AI predictions, RCA insights, financial and ESG projections, plus cross-plant comparisons:
{data}

Return STRICT JSON ONLY in this exact shape:
{
  "executive_summary": "...",
  "key_risks": ["..."],
  "performance_gaps": ["..."],
  "strategic_recommendations": ["..."],
  "confidence": 0-1
}

Rules:
- Keep summaries under 140 words and board-ready.
- Rank risks and gaps by urgency; avoid generic text.
- Recommendations must be actionable and time-bound; avoid hardware changes.
- Confidence must be between 0 and 1.
"""

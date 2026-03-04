from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from app.models.digital_twin import DigitalTwin


@dataclass
class SimulationResult:
    simulated_oee: float
    simulated_health_score: float
    simulated_failure_probability: float
    simulated_energy_efficiency: float
    risk_delta: float
    impact_level: str


_DEF_OEE_DROP_OVERLOAD = 0.08
_DEF_OEE_DROP_SURGE = 0.04
_DEF_OEE_DROP_DRIFT = 0.02


def _clamp(value: float, min_val: float, max_val: float) -> float:
    return max(min_val, min(value, max_val))


def _impact_level(delta: float) -> str:
    if delta >= 15:
        return "HIGH"
    if delta >= 7:
        return "MEDIUM"
    return "LOW"


def _apply_overload(oee: float, health: float, failure: float, energy: float, load_pct: float, degradation_rate: float) -> Dict[str, float]:
    if load_pct == 0:
        return {"oee": oee, "health": health, "failure": failure, "energy": energy}
    load_factor = 1 + (load_pct / 100.0)
    failure += load_factor * degradation_rate * 25.0
    health -= load_factor * degradation_rate * 40.0
    oee -= _DEF_OEE_DROP_OVERLOAD * load_factor
    energy -= 0.05 * load_factor
    return {"oee": oee, "health": health, "failure": failure, "energy": energy}


def _apply_surge(oee: float, health: float, failure: float, energy: float, production_pct: float, degradation_rate: float) -> Dict[str, float]:
    if production_pct == 0:
        return {"oee": oee, "health": health, "failure": failure, "energy": energy}
    surge_factor = production_pct / 100.0
    utilization_pressure = 1 + surge_factor
    oee -= _DEF_OEE_DROP_SURGE * utilization_pressure
    energy -= 0.1 * surge_factor
    failure += utilization_pressure * degradation_rate * 15.0
    health -= utilization_pressure * degradation_rate * 20.0
    return {"oee": oee, "health": health, "failure": failure, "energy": energy}


def _apply_drift(oee: float, health: float, failure: float, energy: float, drift_pct: float) -> Dict[str, float]:
    if drift_pct == 0:
        return {"oee": oee, "health": health, "failure": failure, "energy": energy}
    drift_factor = abs(drift_pct) / 100.0
    failure += drift_factor * 10.0
    health -= drift_factor * 8.0
    oee -= _DEF_OEE_DROP_DRIFT * drift_factor
    energy -= 0.03 * drift_factor
    return {"oee": oee, "health": health, "failure": failure, "energy": energy}


def _apply_manual_adjustment(health: float, failure: float, manual_risk: float) -> Dict[str, float]:
    failure += manual_risk
    health -= manual_risk * 0.4
    return {"health": health, "failure": failure}


def run_simulation(twin: DigitalTwin, params: Dict, simulation_type: str = "composite") -> SimulationResult:
    load_pct = float(params.get("load_pct", 0) or 0)
    production_pct = float(params.get("production_pct", 0) or 0)
    sensor_drift_pct = float(params.get("sensor_drift_pct", 0) or 0)
    manual_risk = float(params.get("manual_risk_adjustment", 0) or 0)

    oee = twin.baseline_oee or 0.0
    health = twin.baseline_health_score or 0.0
    failure = twin.baseline_failure_probability or 0.0
    energy = twin.baseline_energy_efficiency or 0.0
    degradation_rate = twin.degradation_rate or 0.01

    overload = _apply_overload(oee, health, failure, energy, load_pct, degradation_rate)
    oee, health, failure, energy = overload["oee"], overload["health"], overload["failure"], overload["energy"]

    surge = _apply_surge(oee, health, failure, energy, production_pct, degradation_rate)
    oee, health, failure, energy = surge["oee"], surge["health"], surge["failure"], surge["energy"]

    drift = _apply_drift(oee, health, failure, energy, sensor_drift_pct)
    oee, health, failure, energy = drift["oee"], drift["health"], drift["failure"], drift["energy"]

    manual = _apply_manual_adjustment(health, failure, manual_risk)
    health, failure = manual["health"], manual["failure"]

    oee = _clamp(oee, 0.0, 1.0)
    health = _clamp(health, 0.0, 100.0)
    failure = _clamp(failure, 0.0, 100.0)
    energy = max(0.0, energy)

    risk_delta = round(failure - (twin.baseline_failure_probability or 0.0), 2)
    impact = _impact_level(risk_delta)

    return SimulationResult(
        simulated_oee=round(oee, 4),
        simulated_health_score=round(health, 2),
        simulated_failure_probability=round(failure, 2),
        simulated_energy_efficiency=round(energy, 4),
        risk_delta=risk_delta,
        impact_level=impact,
    )

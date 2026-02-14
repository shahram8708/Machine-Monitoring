import os
import random
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Tuple

import requests
from dotenv import load_dotenv

from app import create_app
from app.extensions import db
from app.models.company import Company
from app.models.machine import Machine


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


@dataclass
class MachineProfile:
    name: str
    machine_type: str
    location: str
    idle_temp: float
    normal_temp: float
    heavy_temp: float
    critical_temp: float
    idle_vibration: float
    normal_vibration: float
    heavy_vibration: float
    critical_vibration: float
    idle_current: float
    normal_current: float
    heavy_current: float
    critical_current: float
    base_voltage: float
    voltage_variation: float
    base_speed: float
    base_pressure: float
    base_humidity: float


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class MachineSimulator:
    def __init__(
        self,
        profile: MachineProfile,
        machine_id: int,
        api_token: str,
        base_url: str,
        data_interval: float,
        heartbeat_interval: float,
    ):
        self.profile = profile
        self.machine_id = machine_id
        self.api_token = api_token
        self.data_interval = max(data_interval, 1.0)
        self.heartbeat_interval = max(heartbeat_interval, 5.0)
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.state = "warmup"
        self.state_end = time.time() + random.uniform(20, 45)
        self.fault_temp_drift = 0.0
        self.fault_vib_drift = 0.0
        self.temperature = profile.idle_temp
        self.vibration = profile.idle_vibration
        self.current = profile.idle_current
        self.voltage = profile.base_voltage
        self.pressure = profile.base_pressure * 0.3
        self.humidity = profile.base_humidity
        self.speed = 0.0
        self.last_heartbeat = 0.0

    def _transition_state(self):
        now = time.time()
        if now < self.state_end:
            return

        if self.state == "warmup":
            self.state = "normal"
            self.state_end = now + random.uniform(90, 140)
            return

        roll = random.random()
        if self.state == "idle":
            self.state = "warmup" if roll < 0.7 else "normal"
            self.state_end = now + random.uniform(35, 70)
        elif self.state == "normal":
            if roll < 0.25:
                self.state = "heavy_load"
                self.state_end = now + random.uniform(60, 120)
            elif roll < 0.38:
                self.state = "fault_developing"
                self.state_end = now + random.uniform(80, 180)
            elif roll < 0.55:
                self.state = "idle"
                self.state_end = now + random.uniform(45, 120)
            else:
                self.state_end = now + random.uniform(80, 160)
        elif self.state == "heavy_load":
            if roll < 0.2:
                self.state = "fault_developing"
                self.state_end = now + random.uniform(90, 160)
            else:
                self.state = "normal"
                self.state_end = now + random.uniform(90, 160)
        elif self.state == "fault_developing":
            if roll < 0.25:
                self.state = "critical_overheating"
                self.state_end = now + random.uniform(60, 120)
            elif roll < 0.55:
                self.state = "heavy_load"
                self.state_end = now + random.uniform(80, 150)
            else:
                self.state = "normal"
                self.state_end = now + random.uniform(100, 180)
        elif self.state == "critical_overheating":
            self.state = "idle" if roll < 0.4 else "heavy_load"
            self.state_end = now + random.uniform(90, 180)

    def _load_factor(self) -> float:
        mapping = {
            "idle": 0.08,
            "warmup": 0.35,
            "normal": 0.65,
            "heavy_load": 0.9,
            "fault_developing": 0.82,
            "critical_overheating": 1.0,
        }
        return mapping.get(self.state, 0.65)

    def _approach(self, value: float, target: float, rate: float, jitter: float = 0.0) -> float:
        delta = (target - value) * rate
        noise = random.uniform(-jitter, jitter)
        return value + delta + noise

    def _targets(self) -> Dict[str, float]:
        load = self._load_factor()
        running = self.state != "idle"

        temp_target = self.profile.idle_temp + (self.profile.normal_temp - self.profile.idle_temp) * load
        vib_target = self.profile.idle_vibration + (self.profile.normal_vibration - self.profile.idle_vibration) * load
        current_target = self.profile.idle_current + (self.profile.normal_current - self.profile.idle_current) * load
        pressure_target = max(self.profile.base_pressure * (0.25 + load), 0.1)
        speed_target = self.profile.base_speed * load if running else 0.0

        if self.state == "heavy_load":
            temp_target = self.profile.heavy_temp
            vib_target = self.profile.heavy_vibration
            current_target = self.profile.heavy_current
            speed_target = max(speed_target, self.profile.base_speed * 0.9)
        elif self.state == "fault_developing":
            temp_target = min(self.profile.critical_temp, self.profile.heavy_temp - 2 + self.fault_temp_drift)
            vib_target = min(self.profile.critical_vibration, self.profile.heavy_vibration - 0.2 + self.fault_vib_drift)
            current_target = self.profile.heavy_current - 0.5 + random.uniform(-0.2, 0.6)
        elif self.state == "critical_overheating":
            temp_target = self.profile.critical_temp
            vib_target = self.profile.critical_vibration
            current_target = self.profile.critical_current
            speed_target = self.profile.base_speed * 0.85
            pressure_target = max(pressure_target * 0.95, pressure_target - 1.0)
        elif self.state == "warmup":
            temp_target = max(temp_target, self.profile.idle_temp + 2.0)
            vib_target = max(vib_target, self.profile.idle_vibration * 0.8)
            speed_target = max(speed_target, self.profile.base_speed * 0.4)
        elif self.state == "idle":
            temp_target = max(self.profile.idle_temp - 2, self.temperature - 1.0)
            vib_target = self.profile.idle_vibration * 0.6
            current_target = self.profile.idle_current * 0.3
            pressure_target = max(self.profile.base_pressure * 0.3, self.profile.base_pressure * 0.25)
            speed_target = 0.0

        return {
            "temp": temp_target,
            "vib": vib_target,
            "current": current_target,
            "pressure": pressure_target,
            "humidity": self.profile.base_humidity,
            "speed": speed_target,
            "voltage": self.profile.base_voltage + random.uniform(-self.profile.voltage_variation, self.profile.voltage_variation),
        }

    def _compose_payload(self) -> Dict[str, float]:
        self._transition_state()

        if self.state == "fault_developing":
            self.fault_temp_drift = min(self.fault_temp_drift + 0.25, 12.0)
            self.fault_vib_drift = min(self.fault_vib_drift + 0.08, 3.0)
        elif self.state in {"idle", "normal"}:
            self.fault_temp_drift = max(0.0, self.fault_temp_drift - 0.4)
            self.fault_vib_drift = max(0.0, self.fault_vib_drift - 0.1)

        targets = self._targets()
        self.temperature = self._approach(self.temperature, targets["temp"], rate=0.22, jitter=0.3)
        self.vibration = max(0.05, self._approach(self.vibration, targets["vib"], rate=0.25, jitter=0.05))
        self.current = max(0.0, self._approach(self.current, targets["current"], rate=0.28, jitter=0.08))
        self.voltage = self._approach(self.voltage, targets["voltage"], rate=0.12, jitter=0.15)
        self.pressure = max(0.0, self._approach(self.pressure, targets["pressure"], rate=0.2, jitter=0.05))
        self.humidity = self._approach(self.humidity, targets["humidity"], rate=0.05, jitter=0.1)
        self.speed = max(0.0, self._approach(self.speed, targets["speed"], rate=0.35, jitter=3.0))

        spike_applied = False
        if random.random() < 0.08 and self.state not in {"idle", "critical_overheating"}:
            self.vibration += random.uniform(1.5, 2.8)
            self.current += random.uniform(0.4, 0.9)
            spike_applied = True

        payload = {
            "machine_id": self.machine_id,
            "timestamp": datetime.utcnow().isoformat(),
            "temperature": round(_clamp(self.temperature, 0.0, 130.0), 2),
            "vibration": round(max(self.vibration, 0.05), 3),
            "current": round(max(self.current, 0.0), 3),
            "voltage": round(self.voltage, 2),
            "pressure": round(max(self.pressure, 0.0), 3),
            "humidity": round(_clamp(self.humidity, 10.0, 95.0), 2),
            "speed": round(self.speed, 2),
            "running_status": self.state != "idle",
        }

        state_descriptor = {
            "warmup": "warming up",
            "normal": "running",
            "heavy_load": "load high",
            "idle": "idle cooling",
            "fault_developing": "fault developing",
            "critical_overheating": "critical overheating",
        }.get(self.state, self.state)

        log_line = (
            f"[SIM] {self.profile.name} {state_descriptor} temp={payload['temperature']} "
            f"vibration={payload['vibration']} current={payload['current']}"
        )
        if spike_applied:
            log_line += " spike"
        print(log_line)
        return payload

    def _post_data(self, payload: Dict[str, float]):
        url = f"{self.base_url}/data-ingest"
        try:
            resp = self.session.post(url, json=payload, headers={"X-API-KEY": self.api_token}, timeout=8)
            if resp.status_code >= 400:
                print(f"[SIM][WARN] {self.profile.name} ingest failed {resp.status_code}: {resp.text}")
        except requests.RequestException as exc:
            print(f"[SIM][ERROR] {self.profile.name} ingest error: {exc}")

    def _send_heartbeat(self):
        now = time.time()
        if now - self.last_heartbeat < self.heartbeat_interval:
            return
        url = f"{self.base_url}/heartbeat"
        try:
            resp = self.session.post(url, headers={"X-API-KEY": self.api_token}, timeout=5)
            if resp.status_code >= 400:
                print(f"[SIM][WARN] {self.profile.name} heartbeat failed {resp.status_code}: {resp.text}")
            else:
                print(f"[SIM] {self.profile.name} heartbeat ok")
        except requests.RequestException as exc:
            print(f"[SIM][ERROR] {self.profile.name} heartbeat error: {exc}")
        self.last_heartbeat = now

    def run(self, stop_event: threading.Event):
        while not stop_event.is_set():
            payload = self._compose_payload()
            self._post_data(payload)
            self._send_heartbeat()
            stop_event.wait(self.data_interval)


def _default_profiles() -> List[MachineProfile]:
    return [
        MachineProfile(
            name="CNC-01",
            machine_type="CNC Machine",
            location="Line 1",
            idle_temp=32,
            normal_temp=60,
            heavy_temp=78,
            critical_temp=95,
            idle_vibration=0.4,
            normal_vibration=1.8,
            heavy_vibration=3.6,
            critical_vibration=5.5,
            idle_current=1.5,
            normal_current=6.5,
            heavy_current=10.5,
            critical_current=13.0,
            base_voltage=220,
            voltage_variation=5,
            base_speed=1450,
            base_pressure=3.5,
            base_humidity=45,
        ),
        MachineProfile(
            name="COMP-01",
            machine_type="Air Compressor",
            location="Compressor Room",
            idle_temp=38,
            normal_temp=68,
            heavy_temp=88,
            critical_temp=102,
            idle_vibration=0.6,
            normal_vibration=2.4,
            heavy_vibration=4.2,
            critical_vibration=6.0,
            idle_current=2.5,
            normal_current=9.0,
            heavy_current=14.0,
            critical_current=16.5,
            base_voltage=400,
            voltage_variation=8,
            base_speed=3000,
            base_pressure=9.0,
            base_humidity=50,
        ),
        MachineProfile(
            name="PRESS-01",
            machine_type="Hydraulic Press",
            location="Press Bay",
            idle_temp=35,
            normal_temp=62,
            heavy_temp=82,
            critical_temp=98,
            idle_vibration=0.7,
            normal_vibration=2.0,
            heavy_vibration=3.4,
            critical_vibration=5.2,
            idle_current=3.0,
            normal_current=12.0,
            heavy_current=18.5,
            critical_current=22.0,
            base_voltage=415,
            voltage_variation=10,
            base_speed=900,
            base_pressure=160.0,
            base_humidity=48,
        ),
        MachineProfile(
            name="PKG-01",
            machine_type="Packaging Motor",
            location="Packaging",
            idle_temp=30,
            normal_temp=55,
            heavy_temp=68,
            critical_temp=86,
            idle_vibration=0.3,
            normal_vibration=1.1,
            heavy_vibration=2.1,
            critical_vibration=3.8,
            idle_current=1.2,
            normal_current=6.2,
            heavy_current=9.0,
            critical_current=11.5,
            base_voltage=230,
            voltage_variation=4,
            base_speed=1600,
            base_pressure=4.0,
            base_humidity=47,
        ),
        MachineProfile(
            name="PUMP-01",
            machine_type="Industrial Pump",
            location="Cooling Loop",
            idle_temp=34,
            normal_temp=58,
            heavy_temp=76,
            critical_temp=94,
            idle_vibration=0.5,
            normal_vibration=1.6,
            heavy_vibration=3.0,
            critical_vibration=4.8,
            idle_current=2.0,
            normal_current=8.5,
            heavy_current=12.5,
            critical_current=15.0,
            base_voltage=380,
            voltage_variation=7,
            base_speed=1750,
            base_pressure=8.5,
            base_humidity=52,
        ),
    ]


def _resolve_company(app) -> Company:
    company_name = os.getenv("SIM_COMPANY_NAME")
    with app.app_context():
        if company_name:
            company = Company.query.filter_by(company_name=company_name).first()
            if not company:
                company = Company(company_name=company_name)
                db.session.add(company)
                db.session.commit()
            return company

        existing = Company.query.order_by(Company.id.asc()).first()
        if existing:
            return existing

        company = Company(company_name="Simulation Plant")
        db.session.add(company)
        db.session.commit()
        return company


def _ensure_machines(app, company: Company, profiles: List[MachineProfile]) -> Dict[str, Machine]:
    machines: Dict[str, Machine] = {}
    with app.app_context():
        for profile in profiles:
            machine = Machine.query.filter_by(company_id=company.id, machine_name=profile.name).first()
            if not machine:
                machine = Machine(
                    machine_name=profile.name,
                    machine_type=profile.machine_type,
                    location=profile.location,
                    status="idle",
                    company_id=company.id,
                )
                db.session.add(machine)
                db.session.commit()
            machines[profile.name] = machine
    return machines


def ensure_seed_data(app) -> Tuple[List[MachineProfile], Dict[str, Machine]]:
    with app.app_context():
        db.create_all()

    profiles = _default_profiles()
    company = _resolve_company(app)
    machines = _ensure_machines(app, company, profiles)

    print("[SEED] Database and baseline machine records are ready.")
    return profiles, machines


def main():
    simulation_mode = os.getenv("SIMULATION_MODE", "true").lower() == "true"
    if not simulation_mode:
        print("Simulation disabled (SIMULATION_MODE=false). Exiting.")
        return

    data_interval = float(os.getenv("SIM_DATA_INTERVAL", "5"))
    heartbeat_interval = float(os.getenv("SIM_HEARTBEAT_INTERVAL", "30"))
    base_url = os.getenv("SIM_API_BASE_URL", "http://localhost:5000/api/v1")

    app = create_app()
    profiles, machines = ensure_seed_data(app)

    stop_event = threading.Event()
    simulators: List[threading.Thread] = []

    for profile in profiles:
        machine = machines[profile.name]
        simulator = MachineSimulator(
            profile=profile,
            machine_id=machine.id,
            api_token=machine.api_token,
            base_url=base_url,
            data_interval=data_interval,
            heartbeat_interval=heartbeat_interval,
        )
        thread = threading.Thread(target=simulator.run, args=(stop_event,), daemon=True)
        thread.start()
        simulators.append(thread)
        print(f"[SIM] Started {profile.name} ({profile.machine_type}) -> machine_id={machine.id}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SIM] Stopping simulation...")
        stop_event.set()
        for thread in simulators:
            thread.join(timeout=2)
        print("[SIM] Simulation stopped")


if __name__ == "__main__":
    main()

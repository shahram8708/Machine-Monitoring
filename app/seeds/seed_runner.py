import importlib
import os
import pkgutil
import time
from typing import Callable, Dict, List, Optional

from flask import current_app
from sqlalchemy import inspect

from app.extensions import db
from app.seeds.seed_metadata_model import SeedMetadata

SeedCallable = Callable[[], None]


class SeedDefinition:
    def __init__(self, name: str, fn: SeedCallable, order: int = 1000, description: str | None = None):
        self.name = name
        self.fn = fn
        self.order = order
        self.description = description or ""


class SeedRunner:
    def __init__(self, app):
        self.app = app
        self.enabled = os.getenv("RUN_SEEDS_ON_STARTUP", "false").lower() == "true"
        self.force = os.getenv("FORCE_SEEDS", "false").lower() == "true"
        self.only = {name.strip() for name in os.getenv("ONLY_SEEDS", "").split(",") if name.strip()}

    def run_if_enabled(self):
        if not self.enabled:
            return
        with self.app.app_context():
            self.run_all()

    def run_all(self, specific: Optional[List[str]] = None):
        self._ensure_all_tables()
        self._ensure_seed_metadata_table()
        target = set(specific or [])
        seeds = self._discover_seeds()
        seeds.sort(key=lambda s: (s.order, s.name.lower()))

        applied = {s.name for s in SeedMetadata.query.all()}
        selected = []
        for seed in seeds:
            if self.only and seed.name not in self.only:
                continue
            if target and seed.name not in target:
                continue
            if not self.force and seed.name in applied:
                continue
            selected.append(seed)

        for seed in selected:
            self._run_seed(seed)

    def _run_seed(self, seed: SeedDefinition):
        current_app.logger.info("Running seed: %s", seed.name)
        started = time.perf_counter()
        try:
            seed.fn()
            db.session.commit()
            runtime = time.perf_counter() - started
            db.session.add(
                SeedMetadata(
                    name=seed.name,
                    description=seed.description,
                    runtime_seconds=runtime,
                    success=True,
                )
            )
            db.session.commit()
            current_app.logger.info("Seed %s applied in %.3fs", seed.name, runtime)
        except Exception as exc:  # noqa: BLE001
            db.session.rollback()
            current_app.logger.exception("Seed %s failed: %s", seed.name, exc)
            raise

    def _ensure_seed_metadata_table(self) -> None:
        inspector = inspect(db.engine)
        if "seed_metadata" in inspector.get_table_names():
            return
        current_app.logger.info("Creating seed_metadata tracking table")
        SeedMetadata.__table__.create(bind=db.engine, checkfirst=True)

    def _ensure_all_tables(self) -> None:
        inspector = inspect(db.engine)
        existing = set(inspector.get_table_names())
        if "roles" in existing:
            return
        current_app.logger.info("Creating all tables before seeding (fresh database)")
        db.create_all()

    def _discover_seeds(self) -> List[SeedDefinition]:
        package = "app.seeds"
        seeds: List[SeedDefinition] = []
        package_path = os.path.join(os.path.dirname(__file__))
        for _, module_name, _ in pkgutil.iter_modules([package_path]):
            if not module_name.startswith("seed_"):
                continue
            if module_name in {"seed_runner", "seed_metadata_model"}:
                continue
            module = importlib.import_module(f"{package}.{module_name}")
            fn = getattr(module, "run", None)
            if not callable(fn):
                continue
            meta: Dict[str, object] = getattr(module, "SEED_METADATA", {}) or {}
            name = str(meta.get("name") or module_name)
            order = int(meta.get("order") or 1000)
            description = meta.get("description") or getattr(module, "__doc__", "")
            seeds.append(SeedDefinition(name=name, fn=fn, order=order, description=str(description or "")))
        return seeds

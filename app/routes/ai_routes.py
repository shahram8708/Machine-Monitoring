"""Alias module to keep route structure discoverable.

The actual AI prediction REST endpoints live in app.api.ai_routes and
are registered via the api blueprint. This module exists to satisfy the
routes namespace requirement and can be extended for additional server-rendered
routes if needed.
"""

from app.api.ai_routes import prediction_latest, prediction_history, prediction_plant_summary  # noqa: F401

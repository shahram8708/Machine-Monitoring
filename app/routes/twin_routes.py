"""Alias module to keep route structure discoverable for digital twin APIs.

The REST endpoints live in app.api.twin_routes and are registered via the api blueprint.
This module can be extended for server-rendered routes if needed.
"""

from app.api.twin_routes import (  # noqa: F401
    generate_baseline_api,
    get_twin,
    simulate_twin,
    twin_history,
    twin_what_if,
)

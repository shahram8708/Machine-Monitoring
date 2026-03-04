"""Alias module for RCA endpoints.

The actual REST handlers live in app.api.rca_routes.
"""

from app.api.rca_routes import latest_rca, rca_by_group  # noqa: F401

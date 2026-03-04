"""Alias module to keep alert route namespace discoverable.

API endpoints are implemented in app.api.alert_routes under the /api/v1 prefix.
This module exists for compatibility with route discovery tooling.
"""

from app.api.alert_routes import list_alerts_api, alert_detail_api, acknowledge_alert_api, resolve_alert_api, alert_sla_status_api, alert_analytics_api, unread_alerts_api  # noqa: F401

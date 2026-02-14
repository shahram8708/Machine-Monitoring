from datetime import datetime
from typing import Optional
from flask import request, has_request_context
from flask_login import current_user
from app.extensions import db
from app.models.audit_log import AuditLog


def _get_ip_address() -> Optional[str]:
    if not has_request_context():
        return None
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.remote_addr


def log_action(action: str, entity_type: str, entity_id: int, old_value=None, new_value=None) -> None:
    """Persist an audit log entry without committing the transaction."""
    user_id = current_user.id if has_request_context() and current_user.is_authenticated else None
    log_entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        timestamp=datetime.utcnow(),
        ip_address=_get_ip_address(),
    )
    db.session.add(log_entry)

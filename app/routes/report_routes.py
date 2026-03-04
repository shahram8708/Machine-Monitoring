import mimetypes
import os
from datetime import datetime
from typing import Iterable, Optional

from flask import Blueprint, jsonify, send_file, request
from werkzeug.exceptions import NotFound
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.audit import log_action
from app.decorators import rate_limit, feature_required
from app.extensions import csrf, db
from app.models import User
from app.services.report_service import generate_executive_report, get_report
from app.services.export_service import export_report
from app.services.advanced_report_service import (
    generate_advanced_report,
    list_reports,
    get_report as get_advanced_report,
    delete_report as delete_advanced_report,
)
from config import get_config


report_api_bp = Blueprint("report_api", __name__, url_prefix="/api/reports")

_ALLOWED_ROLES = {
    "SUPER_ADMIN",
    "ENTERPRISE_ADMIN",
    "ADMIN",
    "MANAGER",
    "PLANT_MANAGER",
}


def _resolve_path(path: str | None) -> str | None:
    if not path:
        return None
    if os.path.isabs(path):
        return path
    base = get_config().EXPORT_BASE_DIR
    return os.path.join(base, path)


def _fallback_path(path: str | None) -> str | None:
    resolved = _resolve_path(path)
    if resolved and os.path.exists(resolved):
        return resolved
    # If the path is missing, try locating by basename under export dir.
    base = get_config().EXPORT_BASE_DIR
    legacy_base = os.path.join(os.getcwd(), "generated_reports")
    basename = os.path.basename(path or "")
    if basename:
        candidate = os.path.join(base, basename)
        if os.path.exists(candidate):
            return candidate
        legacy_candidate = os.path.join(legacy_base, basename)
        if os.path.exists(legacy_candidate):
            return legacy_candidate
    # Fallback: if caller passed a relative path that belongs to the legacy folder, try it directly
    legacy_joined = os.path.join(legacy_base, path or "") if path else None
    if legacy_joined and os.path.exists(legacy_joined):
        return legacy_joined
    return resolved


def _latest_from_dirs(extensions: Iterable[str]) -> Optional[str]:
    exts = {ext.lower() for ext in extensions}
    candidates = []
    for base in (get_config().EXPORT_BASE_DIR, os.path.join(os.getcwd(), "generated_reports")):
        if not os.path.isdir(base):
            continue
        try:
            with os.scandir(base) as entries:
                for entry in entries:
                    if entry.is_file():
                        _, ext = os.path.splitext(entry.name)
                        if ext.lower() in exts:
                            candidates.append((entry.stat().st_mtime, entry.path))
        except FileNotFoundError:
            continue
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _guess_mimetype(path: str | None) -> str:
    mime, _ = mimetypes.guess_type(path or "")
    return mime or "application/octet-stream"


def _download_filename(report_type: str, fmt: str | None) -> str:
    ext = (fmt or "pdf").lower()
    if ext == "excel":
        ext = "xlsx"
    return f"advanced-report-{report_type}.{ext}"


def _ensure_report_file(report, user):
    resolved_path = _fallback_path(report.file_path)
    if resolved_path and os.path.exists(resolved_path):
        return resolved_path

    result = generate_advanced_report(user.company_id, user.id, report.report_type, report.format or "PDF", force_regen=True)
    regenerated_path = _fallback_path(result.get("file_path"))
    if regenerated_path and os.path.exists(regenerated_path):
        report.file_path = result.get("file_path")
        report.format = result.get("format", report.format)
        report.generated_at = datetime.utcnow()
        report.generated_by = user.id
        db.session.commit()
        return regenerated_path

    # If regeneration failed, create a placeholder and return it.
    return _placeholder_report(report, user)


def _placeholder_report(report, user):
    company_name = getattr(getattr(user, "company", None), "company_name", "Company")
    placeholder_payload = {
        "kpi_summary": {},
        "health_overview": {},
        "financial_projection": {},
        "esg": {},
        "prediction_outlook": [],
        "ai_summary": {"executive_summary": "Placeholder report regenerated because source file was missing."},
    }
    path = export_report(placeholder_payload, report.format or "PDF", report.report_type, company_name)
    report.file_path = path
    report.generated_at = datetime.utcnow()
    report.generated_by = user.id
    db.session.commit()
    return _fallback_path(path)


def _resolve_user():
    identity = get_jwt_identity()
    try:
        identity_int = int(identity) if identity is not None else None
    except (TypeError, ValueError):
        identity_int = None
    user = User.query.get(identity_int) if identity_int is not None else None
    return user


@report_api_bp.route("/executive", methods=["POST", "GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def executive():
    user = _resolve_user()
    if not user or (user.active_role or "").upper() not in _ALLOWED_ROLES:
        return jsonify({"status": "error", "message": "Forbidden"}), 403

    result = generate_executive_report(user.company_id, user.id)
    log_action("executive_report_generated", "executive_report", result["report_id"], company_id=user.company_id)
    return jsonify(result)


@report_api_bp.route("/generate", methods=["POST"])
@csrf.exempt
@jwt_required()
@rate_limit()
@feature_required("advanced_reports")
def generate_advanced():
    user = _resolve_user()
    if not user or (user.active_role or "").upper() not in _ALLOWED_ROLES:
        return jsonify({"status": "error", "message": "Forbidden"}), 403

    payload = request.get_json() or {}
    report_type = payload.get("report_type", "predictive_maintenance")
    export_format = payload.get("format", "PDF")
    download_now = bool(payload.get("download_now"))

    result = generate_advanced_report(user.company_id, user.id, report_type, export_format, persist=not download_now)

    if download_now:
        resolved_path = _fallback_path(result.get("file_path"))
        if not resolved_path or not os.path.exists(resolved_path):
            regen = generate_advanced_report(user.company_id, user.id, report_type, export_format, force_regen=True, persist=False)
            resolved_path = _fallback_path(regen.get("file_path"))
        if not resolved_path or not os.path.exists(resolved_path):
            return jsonify({"status": "error", "message": "Report file not found"}), 404
        log_action("advanced_report_generated", "advanced_report", result.get("report_id") or 0, company_id=user.company_id, new_value={"report_type": report_type, "format": export_format, "download": True})
        return send_file(
            resolved_path,
            mimetype=_guess_mimetype(resolved_path),
            as_attachment=True,
            download_name=_download_filename(report_type, result.get("format")),
        )

    log_action("advanced_report_generated", "advanced_report", result["report_id"], company_id=user.company_id, new_value={"report_type": report_type, "format": export_format})
    return jsonify(result), 201


@report_api_bp.route("/list", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
@feature_required("advanced_reports")
def list_advanced():
    user = _resolve_user()
    if not user or (user.active_role or "").upper() not in _ALLOWED_ROLES:
        return jsonify({"status": "error", "message": "Forbidden"}), 403

    page = int(request.args.get("page", 1))
    per_page = min(int(request.args.get("per_page", 20)), 100)
    results = list_reports(user.company_id, page=page, per_page=per_page)
    return jsonify(results)


@report_api_bp.route("/<int:report_id>", methods=["DELETE"])
@csrf.exempt
@jwt_required()
@rate_limit()
@feature_required("advanced_reports")
def delete_advanced(report_id: int):
    user = _resolve_user()
    if not user or (user.active_role or "").upper() not in _ALLOWED_ROLES:
        return jsonify({"status": "error", "message": "Forbidden"}), 403

    deleted = delete_advanced_report(report_id, user.company_id)
    if not deleted:
        return jsonify({"status": "error", "message": "Report not found"}), 404

    log_action("advanced_report_deleted", "advanced_report", report_id, company_id=user.company_id)
    return jsonify({"status": "ok", "message": "Report deleted"}), 200


@report_api_bp.route("/download/<int:report_id>", methods=["GET"])
@csrf.exempt
@jwt_required()
@rate_limit()
def download(report_id: int):
    user = _resolve_user()
    if not user or (user.active_role or "").upper() not in _ALLOWED_ROLES:
        return jsonify({"status": "error", "message": "Forbidden"}), 403

    try:
        report = get_advanced_report(report_id, user.company_id)
        resolved_path = _ensure_report_file(report, user)
        if not resolved_path or not os.path.exists(resolved_path):
            fallback_ext = {
                "PDF": {".pdf"},
                "EXCEL": {".xlsx", ".xls"},
                "JSON": {".json"},
            }.get((report.format or "PDF").upper(), {".pdf"})
            latest = _latest_from_dirs(fallback_ext)
            resolved_path = latest if latest and os.path.exists(latest) else _placeholder_report(report, user)
        if not resolved_path or not os.path.exists(resolved_path):
            return jsonify({"status": "error", "message": "Report file not found; regeneration failed"}), 404

        def _stream(path: str):
            download_name = os.path.basename(path) or f"advanced-report-{report.id}.{(report.format or 'pdf').lower()}"
            return send_file(
                path,
                mimetype=_guess_mimetype(path),
                as_attachment=True,
                download_name=download_name,
            )

        log_action("advanced_report_download", "advanced_report", report.id, company_id=user.company_id)
        try:
            return _stream(resolved_path)
        except FileNotFoundError:
            regenerated = _ensure_report_file(report, user)
            if not regenerated or not os.path.exists(regenerated):
                regenerated = _latest_from_dirs({os.path.splitext(resolved_path)[1]}) if resolved_path else None
            if not regenerated or not os.path.exists(regenerated):
                regenerated = _placeholder_report(report, user)
            if regenerated and os.path.exists(regenerated):
                try:
                    return _stream(regenerated)
                except FileNotFoundError:
                    pass
            return jsonify({"status": "error", "message": "Report file not found after regeneration"}), 404
    except NotFound:
        report = None

    if report is None:
        try:
            exec_report = get_report(report_id, user.company_id)
        except NotFound:
            return jsonify({"status": "error", "message": "Report not found"}), 404
        resolved_path = _fallback_path(exec_report.report_path)
        if not resolved_path or not os.path.exists(resolved_path):
            regen = generate_executive_report(user.company_id, user.id)
            resolved_path = _fallback_path(regen.get("path"))
            if resolved_path and os.path.exists(resolved_path):
                exec_report.report_path = regen.get("path")
                db.session.commit()
        if not resolved_path or not os.path.exists(resolved_path):
            return jsonify({"status": "error", "message": "Report file not found after regeneration"}), 404
        log_action("executive_report_download", "executive_report", exec_report.id, company_id=user.company_id)
        try:
            return send_file(resolved_path, mimetype="application/pdf", as_attachment=True, download_name=f"executive-report-{report_id}.pdf")
        except FileNotFoundError:
            return jsonify({"status": "error", "message": "Report file not found"}), 404

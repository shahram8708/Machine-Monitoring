# Machine Monitoring & AI Insights Platform

## 1️⃣ Project Title & Professional Description
- **Project Name:** Machine Monitoring & AI Insights Platform  
- **Short Explanation:** A web system that collects machine sensor data, watches for anomalies, and turns it into live dashboards, alerts, AI-driven maintenance insights, and printable reports.  
- **What this platform is:** A Flask-based industrial monitoring portal with data ingest APIs, alerting, analytics, AI analysis via Google Gemini, reporting, and admin controls.  
- **Problem it solves:** Reduces unplanned downtime by detecting abnormal conditions early, surfacing health scores, and escalating alerts with clear audit trails.  
- **Who should use it:** Plant managers, maintenance engineers, reliability teams, operations leaders, and administrators overseeing multi-site assets.  
- **Where it is useful:** Factories, utilities, energy sites, HVAC plants, logistics hubs—anywhere machines stream telemetry.  
- **Why it exists / motivation:** To unify ingestion, alerting, AI diagnosis, and reporting in one secure, role-aware platform that works even with simulated data for pilots or demos.

## 2️⃣ Table of Contents
- Project Overview
- Key Features
- System Architecture & Tech Stack
- Technical Deep Dive
- Installation & Setup
- Usage Guide
- Environment Variables
- Screens / Pages
- Security & Privacy
- Performance
- Limitations
- Future Enhancements
- Real-World Value
- Contribution
- License
- Conclusion

## 3️⃣ Project Overview (Detailed Explanation)
- **What it does:** Accepts machine telemetry through secure API tokens, stores readings, triggers threshold-based alerts, runs background AI analyses, aggregates hourly/daily stats, and renders dashboards, analytics charts, AI insights, and PDF reports.
- **Platform type:** Web application (Flask) with REST endpoints, background workers, and scheduled jobs.
- **Purpose & goal:** Provide operational visibility, early anomaly detection, and actionable maintenance guidance.
- **Real-world applications:** Predictive maintenance, energy monitoring, shift handover reporting, SLA compliance tracking, and remote asset oversight.
- **Target audience:** Operations managers, maintenance technicians, reliability engineers, and admins who manage users/tenants.
- **Industry relevance:** Industry 4.0, manufacturing, utilities, building management, and fleet assets.
- **Vision & scope:** A single-pane platform for ingest → detect → analyze → alert → report, ready for simulation or production data.

## 4️⃣ Key Features (Extremely Detailed)

**Core features**
- **Secure data ingest API:** Machines post telemetry with `X-API-KEY`; payload validates timestamps, numerics, and running status; rejects mismatched machine IDs; stores raw points.
- **Live status & dashboards:** Role-protected dashboards show machine status, last seen, and latest readings; live endpoints provide JSON for UI refresh.
- **Alerting with escalation:** Threshold checks per sensor create alerts, deduplicate recent ones, and escalate severity over time with email notifications and timelines.
- **AI predictive maintenance (Gemini-2.5-Flash):** Central Gemini service with retry/timeout, structured prompts for failure probability, RUL, degradation, anomaly reasoning, preventive actions, history storage, plant summaries, and polling-friendly REST endpoints.
- **Analytics & trends:** Temperature, vibration, energy, and runtime trends with date ranges; aggregates hourly/daily to reduce load and support long-range views.
- **PDF reporting:** Daily/weekly/monthly/energy reports with runtime, energy, temperature, AI health, risk, and recent alerts exported as PDFs.

**Major features**
- **Role-based access (admin/manager/viewer):** Decorators enforce permissions; admins manage users; managers handle machines/sensors; viewers consume insights.
- **Machine & sensor management:** CRUD for machines (name, type, location, status, install date) and sensors (type, unit, thresholds) with audit logging.
- **Multi-company context:** Active company stored per session; admins can switch companies; queries scoped by company for safety.
- **Audit logging:** User and system actions stored with before/after values, timestamp, and IP when available.

**Minor features**
- **Heartbeat endpoint:** Machines keep “last seen” fresh and auto-recover from offline to idle.
- **Unread alert counter:** Navbar context surfaces recent unresolved alerts.
- **Search & filters:** Machine list supports search by name/type/location; audit page filters by action/entity/user.

**Hidden / backend features**
- **Background scheduler:** Marks stale machines offline, escalates alerts, runs nightly aggregation, triggers predictive scans every 30 minutes, and starts AI worker after app init.
- **Data retention & aggregation:** Raw data purged after retention; hourly stats rolled into daily; energy computed from voltage/current over time windows.
- **Mail notifications:** Escalation levels target managers then admins via configured SMTP.

**Admin / user features**
- **User administration:** Create/edit/deactivate users, set role and company, reset password.
- **Company scoping:** Active company selection for admins; prevents cross-tenant data leakage.
- **Registration/login:** Email/password auth with bcrypt hashing and “remember me” support.

## 5️⃣ System Architecture & Technology Stack
- **Architecture overview:** Flask application factory with blueprints for auth, main, machines, API ingest, analytics, AI, alerts, reports, and admin. Background scheduler (APScheduler) plus a threaded AI worker queue.
- **Frontend technology:** Server-rendered Jinja templates with Bootstrap-style structure; JS assets for live updates and analytics charts.
- **Backend technology:** Flask, SQLAlchemy ORM, Flask-Migrate, Flask-Login, Flask-WTF, Flask-Bcrypt, APScheduler, Flask-Mail.
- **Database:** Configurable via `DATABASE_URL` (defaults to SQLite); models for users, companies, machines, sensors, machine_data, alerts, ai_analysis, hourly/daily stats, audit logs.
- **APIs used:** Google Gemini (`google-genai`) with Google Search grounding tool; internal REST endpoints for ingest/heartbeat and AI/latest/analytics JSON.
- **Libraries & dependencies:** See requirements.txt (Flask, Flask-Login, Flask-WTF, Flask-Bcrypt, Flask-SQLAlchemy, Flask-Migrate, python-dotenv, gunicorn, APScheduler, google-genai, Flask-Mail, reportlab, requests).
- **File structure explanation:** `app/` holds blueprints and services; `models/` defines data schema; `services/` encapsulate alerts and analytics; `ai/` hosts Gemini engine and worker; `reports/` handles PDF export; scheduler.py wires jobs.
- **Component interaction & data flow:**  
  1) Machine sends JSON → `api` blueprint validates, stores `machine_data`, updates status/last_seen.  
  2) Alert service evaluates thresholds and running-state transitions → creates/escalates alerts and timelines.  
  3) AI worker enqueues job per data point → Gemini returns health/risk/anomaly → stored in `ai_analysis`.  
  4) Nightly jobs aggregate raw data → hourly/daily stats → feeds analytics endpoints and reports.  
  5) UI pulls data via blueprints → templates/JS render dashboards, analytics charts, AI panels, alerts, and reports.
- **Request / Response process:** JSON ingest with API key → HTTP 201 on success; heartbeat returns last_seen; AI/latest returns JSON with status/payload; analytics/data returns structured series.
- **Authentication:** Email/password with bcrypt hashes; Flask-Login session cookies (`HttpOnly`, secure in production); role checks via decorators; per-machine API tokens for ingest.
- **Security mechanisms:** CSRF protection on forms, session hardening, per-company scoping, API token validation, alert escalation notification gating.

## 6️⃣ Technical Deep Dive
- **Languages & frameworks:** Python (Flask), Jinja templates, JS for charts/live polling.
- **Dependencies (high-impact):** SQLAlchemy ORM, APScheduler, google-genai client, Flask-Mail, reportlab for PDFs, requests for simulator/API calls.
- **Important modules:**  
  - Application factory and blueprints setup.  
  - Scheduler for offline detection, alert escalation, nightly aggregation.  
  - AI engine (prompt building, JSON coercion, Gemini call with grounding tool).  
  - AI worker (threaded queue, retry with backoff, pending/completed/failed statuses).  
  - Alert service (threshold checks per sensor type, escalation, deduplication, email notifications, timelines).  
  - Analytics service (temperature/vibration series, energy/runtimes from raw or aggregated stats, retention).  
  - Reports service (metrics fetch, PDF layout, recent alerts).  
- **Backend logic:**  
  - Data ingest validates machine token, coerces floats, enforces boolean running_status, timestamps via ISO parsing.  
  - Machine status auto-updates (running/idle) and offline detection via scheduler when stale.  
  - Alerts escalate in severity over time; notification recipients vary by escalation level.  
  - Aggregators compute kWh from voltage/current over intervals, and running/idle hours from status windows.  
- **Frontend logic (high level):** Template-driven pages for login/register, dashboard, machines list/detail/live, AI insights, analytics, alerts list, audit history, reports index, admin user CRUD. JS endpoints supply live data and analytics series.
- **Business logic:** Role-based privileges, per-company scoping, deduplicated alerts, automatic AI analysis per reading, SLA-like escalation cadence, audit trails on critical CRUD and role changes.
- **Algorithms:**  
  - Energy computation integrates $P = V \times I$ over time slices → kWh.  
  - Runtime aggregation sums running/idle seconds across intervals.  
  - Alert escalation steps severity using ordered ladder and time-based cutoff.  
- **Engineering practices:** Background jobs wrapped with app context, retries around AI calls with rollback, input validation on forms and API, deduplication for noisy alerts, late imports to avoid circular dependencies.

## 7️⃣ Installation & Setup Guide (Step-By-Step)
- **System requirements:** Python 3.x, pip, and access to the internet for Gemini API and optional SMTP. SQLite works by default; any SQLAlchemy-supported DB via `DATABASE_URL`.
- **Prerequisites:**  
  - Google Gemini API key.  
  - (Optional) SMTP server for alert emails.  
  - (Optional) Virtual environment for isolation.
- **Setup steps:**  
  1) Clone the repository.  
  2) Create and activate a virtual environment (`python -m venv .venv` then activate).  
  3) Copy .env.example to `.env` and fill values (SECRET_KEY, DATABASE_URL, GEMINI_API_KEY, mail settings).  
  4) Install dependencies: `pip install -r requirements.txt`.  
   5) Initialize DB and seed baseline data: run `python run.py` once (creates tables and seed company/machines if simulation on).  
   6) Apply database migrations (includes AI prediction history): `flask db migrate -m "ai_predictive_engine"` then `flask db upgrade`.  
   7) (Optional) Seed KPI/health samples: run `python -c "from app import create_app; from app.extensions import db; from app.models.machine import Machine; from app.services.kpi_service import compute_daily_kpi; from app.services.health_service import compute_health_score; app=create_app(); ctx=app.app_context(); ctx.push(); [compute_health_score(m) for m in Machine.query.all()]; db.session.commit();"`.  
   8) (Optional) Run simulator to stream demo data: `python seed.py` with `SIMULATION_MODE=true`.  
   9) Start the server: `python run.py` (disables auto-reloader to keep worker stable).
- **How to access:** Open `http://127.0.0.1:5000/` and register a first admin account, or log in if already seeded.
- **Troubleshooting:**  
  - Missing Gemini key → AI analyses stay pending/failed; set `GEMINI_API_KEY`.  
  - SMTP failures → alert timelines note email failure but app continues.  
  - DB lock with SQLite on Windows → avoid multiple concurrent writers; consider Postgres for production.  
  - CSRF errors → ensure forms originate from the site and CSRF token is present.

## 8️⃣ Usage Guide (How to Use the Platform)
- **User interaction flow:**  
  1) Register/login.  
  2) Select active company (admins) or use assigned company.  
  3) Add machines and sensors with thresholds.  
  4) Obtain machine API tokens and configure edge device to POST to `/api/v1/data-ingest` and `/api/v1/heartbeat`.  
  5) Watch dashboards for status, live data, alerts, and AI insights; generate reports as needed.
- **Feature walkthroughs:**  
  - **Data ingest:** Send JSON with `machine_id`, `timestamp` (ISO), `temperature`, `vibration`, `current`, `voltage`, `pressure`, `humidity`, `speed`, `running_status` (bool) using `X-API-KEY`. Success returns stored status; invalid requests explain errors.  
  - **Alerts:** View alert list, resolve when handled; unread count shows in navbar; escalations raise severity automatically.  
  - **Analytics:** Open machine analytics to choose date range and view temperature, vibration, energy, and runtime series.  
  - **AI insights:** Machine AI page shows latest health score, risk, anomaly flag, suggestions, and explanation.  
  - **AI Predictive Dashboard:** Gemini-driven failure probability gauge, 30-day trend, RUL panel, anomaly note, preventive actions, manual run button, and 30–60s polling.  
  - **Reports:** Download daily/weekly/monthly/energy PDFs per machine for handoffs or audits.  
  - **Admin:** Create/edit/deactivate users, set roles and company, switch company context when needed.  
  - **Audit logs:** Review recent actions (filters by action/entity/user).

  ## 1️⃣0️⃣ Quick Testing (API)
  - Get latest prediction: `curl -H "Authorization: Bearer <token>" http://localhost:5000/api/v1/ai/prediction/machine/<id>`  
  - Force new prediction: `curl -X POST -H "Authorization: Bearer <token>" http://localhost:5000/api/v1/ai/prediction/machine/<id>`  
  - Fetch history: `curl -H "Authorization: Bearer <token>" http://localhost:5000/api/v1/ai/prediction/history/<id>`  

## 9️⃣ Environment Variables / Configuration
- `FLASK_ENV` — `development` or `production`; selects config.  
- `SECRET_KEY` — session/signing secret; set a strong value.  
- `DATABASE_URL` — SQLAlchemy URL (default SQLite file).  
- `GEMINI_API_KEY` — required for AI analyses.  
- `GEMINI_MODEL` — defaults to `gemini-2.5-flash`.  
- `GEMINI_TIMEOUT_SECONDS`, `GEMINI_MAX_RETRIES` — network resilience knobs.  
- `AI_FAILURE_THRESHOLD`, `AI_HEALTH_THRESHOLD`, `AI_DEGRADATION_THRESHOLD` — early warning controls.  
- `SIMULATION_MODE` — when true, seeding ensures demo company/machines.  
- `SIM_API_BASE_URL`, `SIM_INGEST_INTERVAL_SECONDS`, `SIM_HEARTBEAT_INTERVAL_SECONDS`, `SIM_DATA_INTERVAL`, `SIM_HEARTBEAT_INTERVAL`, `SIM_COMPANY_NAME` — simulator endpoints and pacing.  
- Mail: `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`.  
- Alerts/time: `ALERT_ESCALATION_MINUTES`, `DEFAULT_TIMEZONE`.

## 🔟 Project Screens / Pages Description
- **Login / Register:** Authentication with email/password; registration collects name, role, company.  
- **Dashboard:** Entry point for authenticated users with navigation to machines, alerts, analytics, AI, reports, audit, admin.  
- **Machines:** List/search machines; create/edit/delete; view detail with sensors; live view for current readings.  
- **Sensors:** Add/edit/delete thresholds per machine.  
- **AI Insights:** Machine-specific page showing latest AI analysis.  
- **Analytics:** Date-range charts for temperature, vibration, energy, runtime.  
- **Alerts:** Paginated list, resolve actions, unread highlights.  
- **Reports:** Machine picker to download PDF summaries (daily/weekly/monthly/energy).  
- **Audit Logs:** Admin-only recent action history with filters.  
- **Admin Users:** Admin-only user management.

## 1️⃣1️⃣ Security & Privacy Notes
- Bcrypt password hashing; no plaintext storage.  
- CSRF protection on form endpoints; API ingest uses token-based auth.  
- Session cookies are `HttpOnly`; marked secure in production config.  
- Role-based authorization on all sensitive routes; company scoping on data queries.  
- API tokens are per-machine; rotate by regenerating the machine token.  
- Email notifications can leak incident details; ensure SMTP channel is secured (TLS/SSL).  
- Store `SECRET_KEY`, `DATABASE_URL`, and `GEMINI_API_KEY` outside version control (.env).

## 1️⃣2️⃣ Performance & Optimization Notes
- Background worker decouples AI calls from ingest to keep write latency low.  
- APScheduler aggregates to hourly/daily stats, reducing query volume for long ranges.  
- Alert checks are lightweight and run inline on ingest; escalations run separately.  
- SQLite is fine for demos; use Postgres/MySQL for higher concurrency.  
- Single-thread AI worker may become a bottleneck under heavy ingest; scale by adding worker processes/queues.

## 1️⃣3️⃣ Limitations & Known Issues
- Single in-process AI worker; no distributed queue.  
- No built-in rate limiting on ingest endpoints.  
- Default SQLite not ideal for concurrent writers or HA.  
- Email delivery depends on SMTP availability; failures noted in alert timelines only.  
- Front-end updates rely on polling endpoints; no WebSocket push.  
- Tests are not provided in the repository.

## 1️⃣4️⃣ Future Enhancements
- Add a real task queue (Celery/RQ) with multiple AI workers.  
- Introduce WebSocket/SSE for real-time dashboards and alert toasts.  
- Add role-scoped API tokens with expiry/rotation and rate limiting.  
- Expand analytics (downtime classification, MTBF/MTTR, cost modeling).  
- Multi-language UI and theme customization.  
- Extend reports with comparisons, KPIs, and per-shift breakdowns.

## 1️⃣5️⃣ Real-World Value & Business Perspective
- Reduces downtime and maintenance costs via early detection and AI suggestions.  
- Provides auditable compliance evidence (alerts, actions, reports).  
- Scales from pilot (simulated data) to production (real machines) with minimal config.  
- Enables service teams and OEMs to offer monitoring-as-a-service.

## 1️⃣6️⃣ Contribution Guidelines (If applicable)
- Fork and create feature branches; keep changes focused.  
- Follow PEP 8 and existing patterns (blueprints, services, models).  
- Include migrations when altering models; keep audit-worthy actions logged.  
- Open a pull request with a clear summary, testing notes, and screenshots for UI changes.

## 1️⃣7️⃣ License Section
- No license file is present. Until a license is added, treat the code as all rights reserved; seek owner approval before reuse or distribution.

## 1️⃣8️⃣ Final Professional Conclusion
This platform unifies telemetry ingest, alerting, AI diagnostics, analytics, and reporting into a single, role-secured web application. It is production-minded (background jobs, escalation, audit trails) yet friendly to pilots through built-in simulation. With clear extension points and a modern Python stack, it can evolve into a full-scale industrial monitoring product.






@"
from app import create_app
from app.extensions import db
from app.models.user import User

app = create_app()
with app.app_context():
    u = User.query.filter_by(email="priya.nair@aurora-precision.com").first()
    if not u:
        raise SystemExit("User not found")
    u.set_password("Aurora!Tech#25")
    u.is_active = True
    db.session.commit()
    print("Password reset for Priya")
"@ | python -
**Machine Monitoring Platform**

- Flask-based industrial monitoring and analytics stack with JWT + session auth, SQLAlchemy ORM, APScheduler jobs, Gemini-powered AI, Razorpay billing, and export/report pipelines.
- Blueprints expose both server-rendered views and REST APIs (prefixed with `/api/v1` plus additional `/api/*` feature namespaces) covering ingestion, KPIs, health, alerts, RCA, digital twins, spare parts, workforce, ESG/financial, advanced analytics, subscriptions, and payments.
- Designed for multi-company, multi-plant tenancy with role and plant scoping, rate limits, feature flags by subscription, and alerting/notification hooks.

**Architecture**
- App factory in [app/__init__.py](app/__init__.py) wires extensions ([app/extensions.py](app/extensions.py)), blueprints (auth/main/admin/machines/api/analytics/reports/etc.), scheduler ([app/scheduler.py](app/scheduler.py)), AI worker, and error handlers; entrypoint [run.py](run.py) seeds data by default (toggle `RUN_SEEDS_ON_STARTUP=false`).
- Persistence via SQLAlchemy models ([app/models](app/models)) covering companies, plants/departments, users/roles/permissions, machines/sensors/data/health/KPIs, alerts/groups/suppression/escalation/RCA, AI analyses/predictions, digital twins/simulations, spares, workforce metrics, subscriptions/payments/usage, advanced/executive reports, and token blocklist.
- Services layer ([app/services](app/services)) encapsulates analytics, alerting, anomaly detection, KPI/health scoring, predictive AI (Gemini), RCA, digital twin/simulation/what-if, ESG/financial, spare parts forecasting, workforce, subscription/usage, notification/email/Slack, exports (PDF/Excel/JSON), payment gateway, caching.
- AI integrates via Gemini with prompt templates ([app/ai/prompt_templates.py](app/ai/prompt_templates.py)) and a lightweight async worker queue ([app/ai/worker.py](app/ai/worker.py)); Google Search grounding supported in [app/ai/gemini_engine.py](app/ai/gemini_engine.py).
- Background jobs (APScheduler) mark offline machines, escalate alerts, run periodic predictions/analytics; alert evaluation also runs on ingest.

**Data & Request Flow**
- Machine ingest: `POST /api/v1/data-ingest` with `X-API-KEY`, body includes `machine_id`, ISO `timestamp`, metrics (temperature, vibration, current, voltage, pressure, humidity, speed), and `running_status` bool; persists [MachineData](app/models/machine_data.py), updates machine status/last_seen, triggers alert evaluation and AI enqueue.
- Heartbeat: `POST /api/v1/heartbeat` with machine token to keep machines online.
- User-facing APIs (JWT/session + role/plant checks, optional CSRF exempt where cookies are not used): KPIs/health (/api/v1/kpi/*, /api/v1/health/*), alerts (/api/v1/alerts*), RCA (/api/v1/rca/*), predictions (/api/v1/ai/prediction/*), comparisons (/api/v1/comparison/*), twins (/api/v1/twin/*), management CRUD (plants/departments/machines/roles/permissions/user-plant), reports (/api/reports/*), advanced analytics (/api/analytics/*), ESG (/api/esg/*), financial (/api/financial/*), spare parts (/api/spare-parts/*), workforce (/api/workforce/*), subscription/usage (/api/subscription/*, /api/usage/*), payments (/api/payment/*).

**Features**
- Multi-tenant RBAC with plant scoping, rate limiting, JWT blocklist, CSRF for form/session flows, feature flags tied to subscription plan, and audit logging.
- Alert lifecycle with grouping, suppression, SLA tracking, escalation, acknowledge/resolve, analytics dashboards, and notification hooks (email/Slack placeholders).
- AI: predictive maintenance scores, RCA explanations, anomaly/correlation insights, what-if analysis for simulations, executive/advanced report summaries via Gemini.
- Digital twins with baselines, simulations, history, and AI what-if interpretations; health/KPI calculations (OEE, MTBF/MTTR, downtime trends).
- Spare parts forecasting and inventory summaries; workforce analytics (load, technician details); ESG and financial risk/impact forecasts.
- Reporting/export: executive PDFs and advanced reports (PDF/Excel/JSON) with regeneration and download safeguards.
- Subscription/billing: plan limits, seat checks, usage metrics, Razorpay subscription creation/verification/webhooks.

**Environment**
- Python 3.11+, Flask, SQLAlchemy, Flask-Migrate, Flask-Login, Flask-JWT-Extended, APScheduler, Flask-Mail, google-genai, Razorpay SDK. See [requirements.txt](requirements.txt).

**Configuration (env vars)**
- Core: `SECRET_KEY`, `DATABASE_URL`, `FLASK_ENV` (development/production), `DEV_SHOW_ALL_USERS_DATA`.
- Auth/JWT: `JWT_SECRET_KEY`, `JWT_ACCESS_MINUTES`, `JWT_REFRESH_DAYS`, `JWT_COOKIE_SECURE`, `JWT_COOKIE_SAMESITE`.
- Rate limiting: `RATE_LIMIT_REQUESTS_PER_MINUTE`, `RATE_LIMIT_BURST`.
- Simulation/data ingest: `SIMULATION_MODE`, `SIM_API_BASE_URL`, `SIM_INGEST_INTERVAL_SECONDS`, `SIM_HEARTBEAT_INTERVAL_SECONDS`.
- AI: `GEMINI_MODEL`, `GEMINI_TIMEOUT_SECONDS`, `GEMINI_MAX_RETRIES`, `AI_FAILURE_THRESHOLD`, `AI_HEALTH_THRESHOLD`, `AI_DEGRADATION_THRESHOLD`.
- Reports/cache: `EXPORT_BASE_DIR`, `CACHE_DEFAULT_TTL_SECONDS`, `REPORT_CACHE_TTL_SECONDS`.
- Payments: `RAZORPAY_KEY_ID`, `RAZORPAY_SECRET`.
- Mail: `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER`.
- Alerts/time: `ALERT_ESCALATION_MINUTES`, `DEFAULT_TIMEZONE`.
- Subscription: `SUBSCRIPTION_CHECK_ENABLED`.
- Seeds: `RUN_SEEDS_ON_STARTUP` (default true; set to false for production).

**Setup (local)**
- Create virtualenv, activate, install deps: `python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt` (on Unix: `source .venv/bin/activate`).
- Set env vars (.env alongside config.py). For Postgres, set `DATABASE_URL=postgresql://...`.
- Initialize DB (if using migrations): `flask db upgrade` with `FLASK_APP=run.py` in env.
- Run: `python run.py` (auto-runs seeds unless disabled).

**Docker**
- Build/run with compose: `cd deployment && docker compose up --build`. Uses [deployment/Dockerfile](deployment/Dockerfile) and [deployment/docker-compose.yml](deployment/docker-compose.yml); binds port 8000.
- Gunicorn config at [deployment/gunicorn.conf.py](deployment/gunicorn.conf.py) (thread workers, timeout 120s).

**Security & Access Control**
- Role enforcement via decorators and `_user_role` checks; plant scoping via user mappings; feature gating via `@feature_required` tied to subscription flags.
- JWT + session auth; CSRF enabled for cookies, exempted for pure API/JWT calls; API tokens for machine ingest via `X-API-KEY`.
- Rate limiting middleware (`RATE_LIMIT_*`) on most APIs; token blocklist via [app/models/token_blacklist.py](app/models/token_blacklist.py).

**Background Jobs & Resilience**
- APScheduler tasks for offline detection, alert escalation/SLA, predictive runs, analytics refresh; ingestion triggers alert evaluation and AI enqueue without blocking writes.
- Report downloads regenerate files when missing and fall back to placeholder to avoid 404s; simulations validate input ranges defensively.

**Limitations / Notes**
- No automated tests are included; add coverage for critical flows (ingest, alerts, AI, billing, permissions).
- Notification channels are stubbed; configure real email/Slack as needed.
- Seeds run on startup by default—disable in production to avoid clobbering data.

**Key Endpoints (non-exhaustive)**
- Ingest/heartbeat: `/api/v1/data-ingest`, `/api/v1/heartbeat`.
- KPIs/health: `/api/v1/kpi/*`, `/api/v1/health/*`, `/api/v1/comparison/*`.
- Alerts/RCA/AI: `/api/v1/alerts*`, `/api/v1/rca/*`, `/api/v1/ai/prediction/*`.
- Twins/simulations: `/api/v1/twin/*` (baseline, simulate, history, what-if).
- Analytics: `/api/analytics/*` (summary, time-series, correlation, ESG, financial, workforce, predictive, twin, risk, export json).
- Domain features: `/api/esg/*`, `/api/financial/*`, `/api/spare-parts/*`, `/api/workforce/*`.
- Reports: `/api/reports/*` (executive, advanced generate/list/download/delete).
- Subscription/billing: `/api/subscription/*`, `/api/usage/*`, `/api/payment/*`.

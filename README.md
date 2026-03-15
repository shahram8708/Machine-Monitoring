# Machine Monitoring — Industrial AI Platform

> A full-stack, production-ready SaaS platform for real-time industrial machine monitoring, AI-powered predictive maintenance, digital twin simulation, and multi-plant operations management.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Project Description](#2-project-description)
3. [Problem Statement](#3-problem-statement)
4. [Solution Overview](#4-solution-overview)
5. [Key Features](#5-key-features)
6. [System Architecture](#6-system-architecture)
7. [Project Workflow](#7-project-workflow)
8. [Technology Stack](#8-technology-stack)
9. [Programming Languages Used](#9-programming-languages-used)
10. [Frameworks and Libraries](#10-frameworks-and-libraries)
11. [Folder Structure Explanation](#11-folder-structure-explanation)
12. [File-by-File Explanation](#12-file-by-file-explanation)
13. [Installation Guide](#13-installation-guide)
14. [Setup Instructions](#14-setup-instructions)
15. [Environment Requirements](#15-environment-requirements)
16. [Dependencies](#16-dependencies)
17. [Configuration Steps](#17-configuration-steps)
18. [How to Run the Project](#18-how-to-run-the-project)
19. [Usage Instructions](#19-usage-instructions)
20. [Code Architecture Explanation](#20-code-architecture-explanation)
21. [API Integrations](#21-api-integrations)
22. [Hardware Components Used](#22-hardware-components-used)
23. [Hardware Architecture](#23-hardware-architecture)
24. [Hardware Setup Instructions](#24-hardware-setup-instructions)
25. [Hardware-Software Interaction](#25-hardware-software-interaction)
26. [Real World Implementation](#26-real-world-implementation)
27. [Data Flow Explanation](#27-data-flow-explanation)
28. [Security Considerations](#28-security-considerations)
29. [Performance Considerations](#29-performance-considerations)
30. [Scalability Discussion](#30-scalability-discussion)
31. [Future Improvements](#31-future-improvements)
32. [Limitations](#32-limitations)
33. [Troubleshooting Guide](#33-troubleshooting-guide)
34. [Frequently Asked Questions](#34-frequently-asked-questions)
35. [Contribution Guidelines](#35-contribution-guidelines)
36. [Version Control Strategy](#36-version-control-strategy)
37. [Testing Strategy](#37-testing-strategy)
38. [Deployment Guide](#38-deployment-guide)
39. [License Section](#39-license-section)
40. [Credits and Acknowledgments](#40-credits-and-acknowledgments)
41. [Conclusion](#41-conclusion)

---

## 1. Project Overview

**Machine Monitoring** is an enterprise-grade Industrial IoT (IIoT) SaaS platform that brings together real-time sensor data ingestion, AI-driven predictive maintenance, digital twin simulation, ESG analytics, financial dashboarding, and workforce management into a single unified web application.

The platform is designed for manufacturing companies operating one or more industrial plants. It collects live telemetry from physical machines (temperature, vibration, current, voltage, pressure, humidity, speed), stores it in a relational database, and feeds it into Google Gemini AI to produce health scores, failure probability scores, remaining useful life estimates, anomaly detections, and root cause analyses — all in near real time.

The system is architected as a Python/Flask web application with a blueprint-based modular structure, JWT-based REST API, APScheduler for background tasks, and a rich JavaScript frontend featuring live charts, digital twin controls, ESG dashboards, and executive CEO reports.

---

## 2. Project Description

At its core, Machine Monitoring provides the following capabilities working in concert:

**Real-time ingestion.** Physical sensors installed on industrial machines push JSON payloads over HTTP to the platform's `/api/v1/data-ingest` endpoint, authenticated with a per-machine API token. Every data point is persisted in the `machine_data` table and immediately triggers AI analysis and alert evaluation.

**AI analysis pipeline.** A dedicated background worker thread dequeues incoming data points and calls the Google Gemini 2.5 Flash model. The model receives a structured sensor snapshot combined with a 24-hour historical summary and returns a JSON payload with health score (0–100), risk level (low/medium/high), anomaly flag, maintenance suggestion, and explanation. Results are stored as `ai_analysis` records.

**Predictive maintenance.** A scheduled job runs every 30 minutes to compute failure probability, remaining useful life (RUL), degradation trend, and preventive action recommendations for each machine — again powered by Gemini using dedicated prompt templates.

**Digital twin simulation.** Each machine has a paired digital twin that stores baseline OEE, health, failure probability, and energy efficiency. Users can run what-if scenarios (overload simulation, production surge, sensor drift) and receive an AI-powered strategic risk assessment.

**Alerts and escalation.** When sensor thresholds are breached, alerts are created with severity levels (LOW, MEDIUM, HIGH, CRITICAL), assigned SLA deadlines, and automatically escalated every 10 minutes if unacknowledged. Alert groups aggregate related alerts for root cause analysis.

**ESG and financial analytics.** The platform calculates energy consumption in kWh from voltage/current readings, derives carbon proxy values, and tracks OEE (Overall Equipment Effectiveness), downtime costs, and revenue impact — giving plant managers and executives a complete operational picture.

**Multi-tenant SaaS.** The application supports multiple companies, each with its own plants, departments, machines, users, and a subscription plan enforced at request time. Payments are processed through Razorpay.

---

## 3. Problem Statement

Manufacturing companies face several interconnected operational challenges that are expensive and difficult to solve without a dedicated technology platform:

**Unplanned downtime.** A machine failure that could have been prevented with early warning costs far more than a scheduled maintenance stop — in lost production, emergency labour, rush-ordered parts, and safety incidents.

**Data silos.** Sensor data typically sits in PLC logs or SCADA systems that are inaccessible to maintenance planners, plant managers, or financial analysts. Decisions are made on incomplete information.

**Reactive maintenance culture.** Without AI-assisted health scoring and failure probability calculations, technicians only respond after a failure occurs rather than scheduling preventive work during planned downtime windows.

**No unified operations view.** ESG targets, spare parts inventory levels, technician performance, financial exposure from downtime, and machine health scores live in separate spreadsheets or siloed tools.

**Difficulty scaling oversight.** A head office overseeing multiple manufacturing plants has no single dashboard showing cross-plant comparisons, fleet-level health, or system-wide alert volumes.

---

## 4. Solution Overview

Machine Monitoring solves all of the above by acting as a unified data hub and intelligence layer sitting between physical machinery and the people who operate and manage it.

Sensors mounted on machines continuously stream readings to the platform over HTTP. The platform immediately evaluates those readings for threshold breaches, queues an AI analysis job, and stores the data for trend analysis. Within seconds of each new reading, the system can tell a technician whether a machine is healthy, degrading, or at imminent risk of failure — and explain why, in plain English, directly from Gemini AI.

The digital twin layer allows plant engineers to run scenarios without touching real machines, understanding the likely impact of running at 120% load or delaying a scheduled calibration.

The CEO dashboard aggregates everything into executive KPIs: plant-level OEE comparisons, fleet health scores, financial exposure from open alerts, ESG sustainability metrics, and AI-generated board-ready summaries.

---

## 5. Key Features

**Machine Management**
Full CRUD for machines with type, location, model number, installation date, cost per hour, revenue per hour, and expected lifetime hours. Each machine is assigned a unique cryptographically-secure API token used to authenticate sensor data submissions.

**Sensor Configuration**
Define multiple sensors per machine (temperature, vibration, current, voltage, pressure, humidity, speed) with calibrated min/max thresholds, accuracy percentage, and calibration date tracking.

**Real-time Live Dashboard**
A live view page polls the server every few seconds and renders Chart.js sparklines for all active sensor streams. Running status, last-seen timestamps, and current readings are displayed in real time.

**AI Health Analysis**
Every incoming data point triggers a Gemini 2.5 Flash call that returns a health score, risk classification, anomaly flag, maintenance suggestion, and explanation. Completed analyses are stored and surfaced on the AI dashboard.

**Predictive Maintenance Engine**
Scheduled every 30 minutes, the predictive service runs four Gemini prompt chains per machine: failure probability, RUL estimation, degradation trend scoring, and preventive action generation.

**Digital Twin and What-If Simulation**
Each machine has a digital twin with baseline OEE, health score, failure probability, and energy efficiency. The simulation engine applies parametric models for overload, production surge, and sensor drift scenarios. Gemini then synthesises a strategic risk assessment and cost impact estimation.

**Root Cause Analysis**
Grouped alerts can be submitted for AI-powered root cause analysis. Gemini analyses alert history, sensor summaries, and failure probability together and returns a primary root cause, contributing factors, sensor interaction explanation, timeline narrative, and probability breakdown per cause.

**Alert Management**
Threshold-based alerts with severity levels, SLA deadlines, acknowledgement tracking, escalation rules, suppression rules, and alert grouping. A scheduler checks every minute and escalates open alerts that exceed the configured SLA window.

**ESG Dashboard**
Energy consumption calculated from voltage/current telemetry, daily kWh series, carbon proxy at 0.4 kg CO2e/kWh, efficiency variance analysis, and AI-generated sustainability improvement suggestions.

**Financial Dashboard**
OEE-linked revenue impact, downtime cost calculation (cost per hour multiplied by downtime duration), spare part expenditure tracking, and financial exposure from open alerts.

**Spare Parts Management**
Spare part catalogue with machine mappings, criticality levels, replacement frequency benchmarks, lead times, supplier information, and inventory levels per plant.

**Workforce Management**
Maintenance task assignment, SLA tracking, technician performance scoring (tasks completed, average resolution time, SLA compliance rate, rework rate), and a technician dashboard.

**Advanced Analytics**
Cross-plant OEE comparisons, machine health heatmaps, hourly and daily aggregated stats, anomaly detection with statistical z-score analysis, and multi-machine comparison reports.

**Executive Reports**
AI-generated board-ready executive summaries combining KPIs, health overview, financial exposure, ESG metrics, and strategic recommendations. Reports can be exported to PDF and Excel.

**Multi-tenant RBAC**
Role hierarchy: SUPER_ADMIN, ENTERPRISE_ADMIN, PLANT_MANAGER, MAINTENANCE_HEAD, TECHNICIAN, VIEWER. Plant-scoped access control ensures technicians see only the machines in their assigned plants.

**Subscription Management**
Tiered SaaS plans with configurable seat limits, machine limits, plant limits, AI prediction quotas, and feature flags (digital twin, advanced reports, workforce analytics). Razorpay payment integration for monthly and yearly billing.

**Audit Logging**
Every sensitive action (role changes, machine creation, alert resolution, user management) is written to an `audit_logs` table with actor ID, IP address, old and new values.

**Email Notifications**
HTML and plain-text email templates for alert notifications, alert escalation, SLA breach warnings, and contact inquiries, delivered via Flask-Mail with configurable SMTP settings.

---

## 6. System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          HARDWARE LAYER                                  │
│  Physical Machines with Sensors (CNC Lathe, Milling, Press, Packaging)  │
│  Microcontroller / Edge Device (Raspberry Pi / Arduino / PLC Gateway)   │
│  Sensors: Temperature, Vibration, Current, Voltage, Pressure, Humidity  │
└──────────────────────────┬───────────────────────────────────────────────┘
                           │  HTTP POST (JSON + X-API-KEY token)
                           ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                     FLASK APPLICATION LAYER                              │
│                                                                          │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────────────────┐  │
│  │  REST API    │  │  Web Blueprints│  │  Background Workers        │  │
│  │  /api/v1/    │  │  (Jinja2 HTML) │  │  APScheduler + AI Thread  │  │
│  │  data-ingest │  │  Dashboard     │  │  Offline Monitor (1min)   │  │
│  │  heartbeat   │  │  Machines      │  │  Alert Escalation (1min)  │  │
│  │  alerts API  │  │  Analytics     │  │  Analytics Aggregation    │  │
│  │  kpi API     │  │  Reports       │  │  (nightly 02:15)          │  │
│  │  twin API    │  │  AI Insights   │  │  Predictive Refresh(30min)│  │
│  └──────┬───────┘  └───────┬────────┘  └────────────────────────────┘  │
│         │                  │                                             │
│  ┌──────▼──────────────────▼────────────────────────────────────────┐   │
│  │                    SERVICE LAYER                                  │   │
│  │  alert_service  health_service  predictive_service  esg_service  │   │
│  │  kpi_service  financial_service  twin_service  rca_service        │   │
│  │  simulation_engine  workforce_service  spare_parts_service        │   │
│  │  analytics_service  report_service  export_service  email_service │   │
│  └──────────────────────────┬────────────────────────────────────────┘  │
│                             │                                            │
│  ┌──────────────────────────▼────────────────────────────────────────┐  │
│  │                    DATA LAYER (SQLAlchemy ORM)                     │  │
│  │  Machine  Sensor  MachineData  AiAnalysis  AIPrediction           │  │
│  │  Alert  AlertGroup  AlertTimeline  RootCauseAnalysis              │  │
│  │  DigitalTwin  TwinSimulationHistory  MachineKPI  MachineHealthScore│  │
│  │  User  Company  Plant  Department  Role  Permission               │  │
│  │  SparePart  SpareInventory  MaintenanceTask  TechnicianPerformance│  │
│  │  CompanySubscription  PaymentTransaction  AuditLog                │  │
│  └──────────────────────────┬────────────────────────────────────────┘  │
│                             │                                            │
│  ┌──────────────────────────▼──────────────────────────────────────┐    │
│  │           SQLite (dev) / PostgreSQL (prod)                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
                             │
                             │  HTTPS (Gemini API calls)
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│               GOOGLE GEMINI 2.5 FLASH (AI Analysis)                      │
│  Health scoring  Failure probability  RUL  Anomaly detection             │
│  Root cause analysis  What-if simulation  ESG optimisation               │
│  Executive summary generation  Advanced report narrative                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Project Workflow

The end-to-end lifecycle of a machine reading through the platform works as follows:

**Step 1 — Hardware data collection.** A sensor node (Raspberry Pi, Arduino, or PLC gateway) reads raw electrical signals from temperature probes, vibration accelerometers, current transformers, voltage sensors, pressure transducers, and humidity sensors. It converts these to engineering units and serialises them as a JSON payload.

**Step 2 — Data ingestion.** The sensor node sends an HTTP POST to `/api/v1/data-ingest` with the machine's API token in the `X-API-KEY` header and the JSON body containing all sensor readings and a running status flag. The server validates the token, validates numeric types, creates a `MachineData` row, updates the machine's `last_seen` timestamp and status, and returns HTTP 201.

**Step 3 — Alert evaluation.** Immediately after saving the data point, `evaluate_alerts_for_datapoint()` compares each reading against sensor thresholds. If any reading breaches its configured limits, an `Alert` record is created with the appropriate severity and an SLA deadline is calculated.

**Step 4 — AI analysis queue.** The data point ID is pushed onto an in-memory queue consumed by a dedicated background worker thread. The worker calls `run_ai_analysis()`, which constructs a prompt with the current snapshot and a 24-hour statistical summary, then calls Gemini. The response is parsed and stored as an `AiAnalysis` record.

**Step 5 — Scheduled jobs.** Every 30 minutes, the predictive refresh job runs failure probability, RUL, degradation, and preventive action chains for each machine. Every minute, the alert escalation job checks for alerts older than the SLA deadline and escalates them, sending email notifications. Every night at 02:15, the nightly aggregation job rolls up hourly machine stats into daily summaries.

**Step 6 — Offline detection.** Every minute, a scheduler job queries machines whose `last_seen` timestamp is older than 2 minutes and transitions them to `offline` status, logging an audit event.

**Step 7 — Dashboard rendering.** When a user logs into the web interface, the appropriate dashboard template is served based on their role. JavaScript running in the browser polls the REST API endpoints to refresh charts, health indicators, and alert counts at regular intervals.

**Step 8 — Digital twin simulation.** A user can open a machine's digital twin view, configure a what-if scenario (e.g., +25% production surge), click Simulate, and receive an immediate simulation result from the Python engine plus an AI strategic assessment from Gemini.

---

## 8. Technology Stack

| Category | Technology |
|---|---|
| Backend Framework | Flask 3.x (Python) |
| ORM | Flask-SQLAlchemy |
| Database Migration | Flask-Migrate (Alembic) |
| Authentication | Flask-Login (session), Flask-JWT-Extended (API tokens) |
| Password Hashing | Flask-Bcrypt |
| CSRF Protection | Flask-WTF (CSRFProtect) |
| Email | Flask-Mail |
| Scheduler | APScheduler (BackgroundScheduler) |
| AI Engine | Google Gemini 2.5 Flash (via google-genai SDK) |
| Payment | Razorpay Python SDK |
| Report Export | ReportLab (PDF), openpyxl (Excel) |
| HTTP Client | requests |
| Markdown Rendering | markdown + bleach |
| Frontend | Jinja2 templates, Vanilla JavaScript, Chart.js |
| Styling | Custom CSS (style.css, analytics.css) |
| Containerisation | Docker, Docker Compose |
| WSGI Server | Gunicorn (gthread worker, multi-process) |
| Database | SQLite (development), PostgreSQL (production) |
| Environment Config | python-dotenv |

---

## 9. Programming Languages Used

**Python 3.11** is the primary backend language. Every route, service, model, scheduler job, seed script, and utility is written in Python. The project follows a clean package structure with `__init__.py` files in every module.

**JavaScript (ES6)** powers all the frontend interactivity. Separate JS files handle each dashboard section: live sensor charts (`live.js`), AI insights (`ai_insights.js`), digital twin simulation (`digital_twin.js`), ESG charts (`esg.js`), financial dashboards (`financial.js`), workforce analytics (`workforce.js`), spare parts tracking (`spare_parts.js`), and more.

**HTML5 with Jinja2 templating** renders all web pages server-side. Templates inherit from `base.html` and use Jinja2 blocks for page-specific content, navigation injection, and context variables.

**CSS3** provides all styling through two main stylesheets: `style.css` for global layout and components, and `analytics.css` for the analytics-specific dashboard elements.

**SQL** underlies all data access through SQLAlchemy ORM, with raw SQL occasionally used for complex aggregation queries via `func.avg`, `func.sum`, and `func.count`.

---

## 10. Frameworks and Libraries

**Flask** provides the WSGI application, request routing via blueprints, template rendering, session management, and extension integration.

**SQLAlchemy** handles all database interactions through a Python ORM layer, with `DevBypassQuery` subclass enabling a development mode that bypasses company/user scoping filters for easier local testing.

**Flask-JWT-Extended** issues short-lived access tokens (default 15 minutes) and longer-lived refresh tokens (7 days) for REST API authentication. A token blacklist stored in the database allows immediate revocation.

**APScheduler** runs four scheduled jobs within the Flask application context: machine offline detection, alert escalation, nightly analytics aggregation, and predictive maintenance refresh.

**google-genai SDK** provides the Python client for Google Gemini. The engine configures a `GoogleSearch` grounding tool for Gemini to consult external knowledge when needed, ensuring analysis is not limited to training data.

**Chart.js** (loaded from CDN in browser) renders all time-series charts, bar charts, doughnut charts, and scatter plots on the frontend dashboards.

**ReportLab** generates PDF exports of machine reports and executive summaries.

**openpyxl** generates Excel workbooks for data exports.

**Razorpay** Python SDK handles subscription payment creation, order verification, and webhook signature validation.

**bleach** sanitises HTML output from the Markdown renderer to prevent XSS in AI-generated content displayed in the browser.

---

## 11. Folder Structure Explanation

```
Machine-Monitoring-main/
│
├── run.py                      Entry point — creates Flask app and runs development server
├── config.py                   Configuration classes for development and production
├── requirements.txt            Python package dependencies
├── .env.example                Template for environment variable configuration
├── .gitignore                  Git ignore rules
│
├── app/                        Main application package
│   ├── __init__.py             Application factory (create_app), blueprint registration,
│   │                           scheduler init, JWT setup, subscription guard middleware
│   ├── extensions.py           Flask extension instances (db, migrate, login_manager, etc.)
│   ├── scheduler.py            APScheduler job definitions and initialisation
│   ├── security.py             Active company resolution and session management helpers
│   ├── audit.py                Audit log helper (log_action)
│   │
│   ├── models/                 SQLAlchemy ORM models (one file per entity)
│   ├── api/                    REST API blueprints (data ingestion, alerts, KPIs, twin, RCA)
│   ├── ai/                     AI engine (Gemini client, worker thread, prompt templates)
│   ├── auth/                   Authentication blueprint (login, register, logout)
│   ├── main/                   Main blueprint (dashboard, index)
│   ├── machines/               Machine CRUD blueprint
│   ├── analytics/              Analytics dashboard blueprint
│   ├── alerts/                 Alert list blueprint
│   ├── reports/                Reports index blueprint
│   ├── admin/                  Admin user management blueprint
│   │
│   ├── routes/                 Additional feature blueprints
│   │   ├── spare_routes.py     Spare parts management
│   │   ├── workforce_routes.py Workforce and maintenance task management
│   │   ├── financial_routes.py Financial dashboard
│   │   ├── esg_routes.py       ESG sustainability dashboard
│   │   ├── rca_routes.py       Root cause analysis dashboard
│   │   ├── twin_routes.py      Digital twin dashboard
│   │   ├── report_routes.py    Advanced report generation API
│   │   ├── subscription_routes.py  Subscription and usage management
│   │   ├── payment_routes.py   Razorpay payment processing
│   │   ├── ai_routes.py        AI prediction dashboard routes
│   │   └── analytics_routes.py Advanced analytics routes
│   │
│   ├── services/               Business logic layer (one file per domain)
│   ├── seeds/                  Database seed scripts (one per entity, ordered execution)
│   ├── decorators/             Reusable route decorators (RBAC, rate limiting, feature flags)
│   ├── utils/                  Utility functions (Markdown renderer)
│   │
│   ├── static/
│   │   ├── css/                Global and analytics stylesheets
│   │   └── js/                 Feature-specific JavaScript modules
│   │
│   └── templates/              Jinja2 HTML templates
│       ├── base.html           Master layout with navigation and alert bar
│       ├── dashboard.html      Main dashboard
│       ├── dashboard/          Role-specific dashboard templates
│       ├── machines/           Machine CRUD and live view templates
│       ├── auth/               Login and register templates
│       ├── admin/              User management templates
│       ├── alerts/             Alert list template
│       ├── analytics/          Analytics dashboard template
│       ├── ai/                 AI insights template
│       ├── reports/            Reports index template
│       ├── audit/              Audit history template
│       └── emails/             HTML and plain-text email templates
│
├── deployment/
│   ├── Dockerfile              Python 3.11-slim container definition
│   ├── docker-compose.yml      Single-service compose configuration
│   └── gunicorn.conf.py        Gunicorn workers, threads, and bind configuration
│
└── instance/
    └── app.db                  SQLite database file (development only)
```

---

## 12. File-by-File Explanation

### Root Level

**`run.py`** — The entry point for the development server. It calls `create_app()` from the application factory and optionally runs seed data on startup via `SeedRunner`. The `use_reloader=False` flag prevents APScheduler from starting twice during the Werkzeug reloader cycle.

**`config.py`** — Defines three configuration classes: `Config` (base), `DevelopmentConfig` (debug enabled, subscription check disabled by default), and `ProductionConfig` (secure cookies, no debug). All values are read from environment variables with sensible defaults. Notable settings include `SIMULATION_MODE` for enabling a built-in data simulator, all Gemini model parameters, Razorpay keys, SMTP settings, JWT token lifetimes, and rate limiting parameters.

**`requirements.txt`** — Lists all Python dependencies without pinned versions, keeping the project easy to update.

**`.env.example`** — A complete template of every environment variable the application reads, with placeholder values that must be replaced before running the project.

### `app/__init__.py`

The application factory. Creates the Flask app, binds all extensions, registers all blueprints, configures the login manager, starts the scheduler, launches the AI worker thread, installs a subscription guard middleware (enforces active subscription on every request), and registers error handlers for a full range of HTTP status codes.

### `app/extensions.py`

Instantiates all Flask extensions as module-level objects so they can be imported across the application without circular dependencies. Also defines `DevBypassQuery`, a SQLAlchemy query subclass that strips company/user ID filters when the `DEV_SHOW_ALL_USERS_DATA` config flag is set, making local development across multiple tenants much easier.

### `app/scheduler.py`

Defines and starts four APScheduler jobs:
`offline_monitor` — runs every minute, marks machines offline if their `last_seen` is more than 2 minutes old.
`analytics_aggregation` — cron at 02:15 UTC daily, rolls up machine hourly stats.
`alert_escalation` — runs every minute, escalates overdue alerts and sends email notifications.
`predictive_refresh` — runs every 30 minutes, runs full predictive analysis chains for all machines.

### `app/security.py`

Provides `get_active_company_id()`, `set_active_company()`, and `clear_active_company()`. SUPER_ADMIN and ENTERPRISE_ADMIN users can switch the active company they are viewing via a session variable. All other users always see their own company's data.

### `app/audit.py`

Contains the `log_action()` helper that writes audit log entries. Automatically captures the current user ID and IP address from the request context.

### AI Module (`app/ai/`)

**`gemini_engine.py`** — The lowest-level Gemini integration. Configures the `genai.Client` with the API key from environment, attaches a `GoogleSearch` grounding tool, constructs prompts from the current sensor snapshot combined with a 24-hour statistical history window, calls Gemini, extracts JSON from the response, validates and normalises the fields, and returns a clean Python dictionary.

**`worker.py`** — Implements a thread-safe producer/consumer queue. `init_ai_worker()` starts a daemon thread that loops forever, dequeuing jobs and calling `run_ai_analysis()`. Jobs are enqueued by the data ingestion endpoint immediately after saving each new `MachineData` row. Analysis records are created in `pending` status before the job is processed and updated to `completed` or `failed` after.

**`prompt_templates.py`** — Defines all Gemini prompt strings as module-level constants. Each prompt instructs Gemini to return strict JSON, specifies the exact output schema, and includes explicit rules about staying within provided data, maintaining consistency, and avoiding prose outside the JSON block. Templates cover failure probability, RUL estimation, anomaly detection, degradation analysis, preventive actions, root cause analysis, what-if simulation, ESG improvement, executive summary, and advanced report summary.

**`routes.py`** — Handles the `/ai/insights` page that displays the AI analysis history for a selected machine with filterable health scores and risk levels.

### API Module (`app/api/`)

**`routes.py`** — The two most critical API endpoints. `/api/v1/data-ingest` (POST) authenticates via `X-API-KEY` header, validates the JSON payload types, creates `MachineData`, triggers alert evaluation and AI analysis. `/api/v1/heartbeat` (POST) updates `last_seen` without a full data payload, keeping machines online during idle periods.

**`alert_routes.py`** — REST endpoints for acknowledging and resolving alerts, listing alerts with filters, and retrieving alert timelines.

**`kpi_routes.py`** — REST endpoints for fetching machine KPI data for chart rendering on dashboards.

**`twin_routes.py`** — REST endpoints for digital twin simulation: `POST /run` submits a simulation scenario, `GET /history` returns past simulations for a machine.

**`rca_routes.py`** — REST endpoint for triggering AI root cause analysis on an alert group.

**`management_routes.py`** — Admin endpoints for managing users and company settings.

**`ai_routes.py`** — REST endpoint for triggering on-demand AI predictions.

### Models (`app/models/`)

**`machine.py`** — The central model. Stores machine identity, type, code, location, installation date, running status, cost/revenue per hour, expected lifetime, and `last_seen`. Relationships to sensors, data points, AI analyses, alerts, KPIs, health scores, predictions, and digital twin.

**`sensor.py`** — Represents a single sensor type attached to a machine. Stores type (temperature, vibration, etc.), unit, calibration date, accuracy, and min/max thresholds for alert evaluation.

**`machine_data.py`** — The time-series table. Each row stores one reading: timestamp, temperature, vibration, current, voltage, pressure, humidity, speed, and running status. Compound indexes on `(machine_id, timestamp)` and `(machine_id, created_at)` for fast time-range queries. Also provides `get_latest_machine_data()` and `get_last_1_hour_data()` convenience functions.

**`ai_analysis.py`** — Stores completed AI analysis results: health score, risk level, anomaly flag, maintenance suggestion, explanation, and status (pending/completed/failed).

**`ai_prediction.py`** — Stores scheduled predictive analysis results: failure probability, RUL hours, degradation trend score, anomaly score, and all JSON output fields from each Gemini chain.

**`alert.py`** — The alert model with severity, SLA deadline, acknowledgement tracking, escalation level, priority score, alert grouping, and a rich `AlertTimeline` child model for event history.

**`alert_group.py`** — Groups related alerts for root cause analysis and aggregate analytics.

**`root_cause_analysis.py`** — Stores Gemini RCA output: primary cause, contributing factors, probability breakdown, timeline explanation, sensor interactions, and confidence score.

**`digital_twin.py`** — Stores the baseline operating profile of a machine: OEE, health score, failure probability, and energy efficiency. The `TwinSimulationHistory` child model stores each what-if scenario run with input parameters and simulated results.

**`machine_health.py`** — Stores computed health scores with the calculation timestamp.

**`machine_kpi.py`** — Stores daily KPI snapshots: OEE, availability, performance, quality, downtime minutes, production count, and defect count.

**`machine_stats.py`** — Stores hourly and daily aggregated statistics (averages, min/max) for efficient chart rendering without querying raw time-series data.

**`user.py`** — Stores user identity, hashed password, role, company association, and plant mappings. The `is_admin` property checks the active role against admin role names. An SQLAlchemy event listener automatically writes an audit log entry whenever a user's role is changed.

**`company.py`** — The top-level tenant entity. All other data is scoped to a company.

**`plant.py`** — Represents a physical manufacturing facility belonging to a company. Machines and users are assigned to plants.

**`department.py`** — Represents organisational departments within a plant (Production, Maintenance, Quality, etc.).

**`subscription.py`** — Three related models: `SubscriptionPlan` (feature flags, limits), `CompanySubscription` (activation dates, seat counts, Razorpay subscription ID), `SeatAllocation` (per-user seat assignment), and `PaymentTransaction` (payment records with Razorpay IDs and signature verification flag).

**`spare_parts.py`** — Spare part catalogue with machine mappings and criticality levels.

**`workforce.py`** — Technician performance records and maintenance task tracking.

**`audit_log.py`** — Immutable audit log entries with actor, IP, action type, entity, and old/new values stored as JSON.

**`token_blacklist.py`** — Revoked JWT tokens stored by JTI for immediate invalidation.

**`usage_analytics.py`** — Platform usage metrics for SaaS analytics.

**`executive_report.py`** — Cached AI-generated executive reports.

**`escalation_rule.py`** and **`alert_suppression_rule.py`** — Configurable per-company escalation timing and alert noise suppression rules.

### Services (`app/services/`)

The service layer is where all business logic lives. Each file corresponds to one domain:

**`alert_service.py`** — `evaluate_alerts_for_datapoint()` queries sensors with violated thresholds and creates/updates alerts. `escalate_open_alerts()` is called by the scheduler.

**`health_service.py`** — Computes composite health scores by combining sensor threshold breach severity, recent AI analysis scores, and downtime frequency.

**`predictive_service.py`** — Coordinates the four Gemini predictive chains, assembles input context from KPIs, health scores, recent data, and alert history, and saves `AIPrediction` records.

**`anomaly_service.py`** — Computes z-scores for each sensor channel over a rolling time window, identifies outliers, and optionally submits findings to Gemini for validation.

**`simulation_engine.py`** — Pure Python parametric simulation. Applies mathematical models for overload (`_apply_overload`), production surge (`_apply_surge`), and sensor drift (`_apply_drift`) to baseline digital twin values and returns a `SimulationResult` dataclass.

**`twin_service.py`** — Orchestrates digital twin simulation: calls the simulation engine, invokes Gemini for strategic assessment, persists `TwinSimulationHistory`, and returns combined results.

**`rca_service.py`** — Assembles alert group context and calls Gemini with the `root_cause_analysis_prompt` template.

**`esg_service.py`** — Calculates energy consumption series from voltage/current readings, derives carbon proxy, and calls Gemini for sustainability improvement suggestions.

**`financial_service.py`** — Calculates downtime cost (cost per hour × downtime duration), OEE-linked revenue impact, spare part expenditure, and total financial exposure from open alerts.

**`kpi_service.py`** — Reads and aggregates KPI data for dashboard charts.

**`analytics_service.py`** — `run_nightly_aggregation()` processes raw machine data into hourly stats. Advanced analytics methods calculate cross-plant comparisons and heatmap data.

**`report_service.py`** and **`advanced_report_service.py`** — Generate structured report data and call Gemini for narrative summaries.

**`export_service.py`** — Generates PDF exports via ReportLab and Excel workbooks via openpyxl.

**`email_service.py`** — Renders Jinja2 email templates and sends messages via Flask-Mail.

**`notification_service.py`** — Orchestrates alert notification delivery across channels.

**`subscription_service.py`** — Validates subscription status, checks feature flags, enforces machine and seat limits.

**`payment_service.py`** — Creates Razorpay orders and verifies payment signatures.

**`scope_service.py`** — Provides company-scoped query helpers used by routes.

**`cache_service.py`** — Simple in-process TTL cache for report data (configurable TTL via environment).

**`gemini_service.py`** — Wrapper around the Gemini client with retry logic (configurable `GEMINI_MAX_RETRIES`) and timeout handling.

**`comparison_service.py`** — Cross-machine and cross-plant comparative analytics.

**`whatif_service.py`** — What-if analysis service integrating simulation engine with Gemini assessment.

**`usage_service.py`** — Tracks API call counts and feature usage for SaaS metering.

**`workforce_service.py`** — Aggregates technician performance data and maintenance SLA metrics.

**`spare_parts_service.py`** — Inventory alerts, criticality assessment, and reorder recommendations.

### Seeds (`app/seeds/`)

The seeds directory contains 40+ individual seed scripts, one per entity type, each with a `SEED_METADATA` dictionary specifying name, order, and description. `seed_runner.py` reads all seed modules, sorts them by order, and executes them in dependency order. This allows the application to start with a fully populated demo dataset automatically when `SEED_ON_START=true`.

### Decorators (`app/decorators/`)

**`role_required.py`** — Parameterised decorator that enforces role-based access. Convenience wrappers `manager_required` and `admin_required` cover common patterns.

**`plant_scope_required.py`** — Ensures the current user has access to the plant referenced in the request.

**`rate_limit.py`** — Per-endpoint rate limiting using `api_rate_limit` records stored in the database, configurable via environment variables.

**`feature_flag.py`** — Checks subscription plan feature flags before allowing access to premium features like digital twin or workforce analytics.

### Deployment Files

**`Dockerfile`** — Multi-stage-free slim build based on Python 3.11-slim. Installs build tools and `libpq-dev` (for psycopg2), copies the application, exposes port 8000, and starts Gunicorn.

**`docker-compose.yml`** — Single-service compose file that builds from the parent directory, maps port 8000, mounts the project volume for development, and reads the `.env` file.

**`gunicorn.conf.py`** — Configures Gunicorn with `gthread` worker class, `cpu_count * 2 + 1` worker processes, 4 threads per worker, and 120-second timeout — suitable for production workloads with mixed IO-bound and CPU-bound work.

---

## 13. Installation Guide

**Prerequisites**
Python 3.11 or higher must be installed on the target machine. Verify with `python3 --version`.
A Google Gemini API key from Google AI Studio (https://aistudio.google.com/) is required for AI features.
A Razorpay account (https://razorpay.com/) is required for payment processing in production.
Node.js is not required — all frontend JavaScript is served as static files.
Docker and Docker Compose are optional but recommended for production deployment.

**Step 1 — Clone or extract the repository**
```bash
git clone https://github.com/shahram8708/Machine-Monitoring.git
cd machine-monitoring
```

Or extract the ZIP archive:
```bash
unzip Machine-Monitoring-main.zip
cd Machine-Monitoring-main
```

**Step 2 — Create and activate a virtual environment**
```bash
python3 -m venv venv
source venv/bin/activate        # Linux / macOS
venv\Scripts\activate           # Windows
```

**Step 3 — Install Python dependencies**
```bash
pip install -r requirements.txt
```

**Step 4 — Create the environment file**
```bash
cp .env.example .env
```
Edit `.env` and fill in your actual values (see Configuration Steps section).

**Step 5 — Initialise the database**
For SQLite (development):
```bash
flask db upgrade
```
For PostgreSQL (production), set `DATABASE_URL` in `.env` first, then run the same command.

**Step 6 — Start the application**
```bash
python run.py
```
On first launch with `SEED_ON_START=true`, the seed runner populates demo companies, plants, machines, sensors, users, and historical data automatically. This takes approximately 15–30 seconds.

---

## 14. Setup Instructions

After the initial installation, configure the following:

**Database migrations** are managed with Flask-Migrate. After any model change, generate a migration script:
```bash
flask db migrate -m "description of change"
flask db upgrade
```

**Creating an admin user** — the seed scripts create default users including a SUPER_ADMIN account. Check `app/seeds/seed_users.py` for the email address and use the password set in `SEED_USER_PASSWORD` (default: `Welcome#2026`).

**Registering a machine** — log in as an admin, navigate to Machines, click Add Machine, fill in the form including cost and revenue per hour, and save. The machine's API token is auto-generated and displayed on the machine detail page.

**Configuring sensors** — on the machine detail page, click Add Sensor. Configure the sensor type, unit, and min/max thresholds. Multiple sensors can be added per machine.

**Connecting physical hardware** — copy the machine's API token and configure it in the edge device firmware or script (see Hardware Setup Instructions).

---

## 15. Environment Requirements

| Variable | Description | Default |
|---|---|---|
| `FLASK_ENV` | Application environment (`development` or `production`) | `development` |
| `SECRET_KEY` | Flask session signing key | `change-this-secret` |
| `DATABASE_URL` | SQLAlchemy database URI | `sqlite:///app.db` |
| `JWT_SECRET_KEY` | JWT signing key | `change-this-jwt-secret` |
| `JWT_ACCESS_MINUTES` | Access token lifetime in minutes | `15` |
| `JWT_REFRESH_DAYS` | Refresh token lifetime in days | `7` |
| `GEMINI_API_KEY` | Google Gemini API key | (required) |
| `GEMINI_MODEL` | Gemini model name | `gemini-2.5-flash` |
| `SIMULATION_MODE` | Enable built-in data simulator | `true` |
| `SIM_API_BASE_URL` | Base URL for simulation API calls | `http://127.0.0.1:5000/api/v1` |
| `SIM_INGEST_INTERVAL_SECONDS` | Simulation data push interval | `5` |
| `AI_FAILURE_THRESHOLD` | Failure probability threshold for alerts | `65` |
| `AI_HEALTH_THRESHOLD` | Health score threshold for alerts | `60` |
| `AI_DEGRADATION_THRESHOLD` | Degradation score threshold for alerts | `70` |
| `MAIL_SERVER` | SMTP server hostname | `smtp.gmail.com` |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USE_TLS` | Enable STARTTLS | `true` |
| `MAIL_USERNAME` | SMTP authentication username | (optional) |
| `MAIL_PASSWORD` | SMTP authentication password | (optional) |
| `RAZORPAY_KEY_ID` | Razorpay public key ID | (required for payments) |
| `RAZORPAY_SECRET` | Razorpay secret key | (required for payments) |
| `ALERT_ESCALATION_MINUTES` | Minutes before alert escalation | `10` |
| `SEED_ON_START` | Run seed scripts on startup | `true` |
| `SEED_USER_PASSWORD` | Default password for seeded users | `Welcome#2026` |

---

## 16. Dependencies

All dependencies are listed in `requirements.txt`. Key packages and their purpose:

`Flask` — web framework and WSGI application. `Flask-Login` — session-based user authentication. `Flask-WTF` — CSRF protection and form handling. `Flask-Bcrypt` — Bcrypt password hashing. `Flask-SQLAlchemy` — ORM and database session management. `Flask-Migrate` — database schema versioning via Alembic. `Flask-Mail` — email sending. `Flask-JWT-Extended` — JWT token issuance and validation. `python-dotenv` — loads `.env` file into environment. `APScheduler` — background job scheduling. `google-genai` — Google Gemini AI client. `psycopg2-binary` — PostgreSQL adapter. `reportlab` — PDF generation. `openpyxl` — Excel file generation. `requests` — HTTP client for simulation mode API calls. `markdown` — Markdown text rendering. `bleach` — HTML sanitisation for safe display of AI output. `email-validator` — email address validation in registration forms. `razorpay` — payment gateway integration. `gunicorn` — production WSGI server.

---

## 17. Configuration Steps

**1. Set a strong `SECRET_KEY`** — generate a random string: `python3 -c "import secrets; print(secrets.token_hex(32))"`

**2. Set a strong `JWT_SECRET_KEY`** — generate separately from the session key.

**3. Configure the Gemini API key** — obtain from https://aistudio.google.com/ and set `GEMINI_API_KEY`.

**4. Configure the database** — for SQLite development, the default `sqlite:///app.db` works. For PostgreSQL production: `DATABASE_URL=postgresql://user:password@host:5432/dbname`.

**5. Configure email** — for Gmail: set `MAIL_SERVER=smtp.gmail.com`, `MAIL_PORT=587`, `MAIL_USE_TLS=true`, `MAIL_USERNAME=your@gmail.com`, `MAIL_PASSWORD=your_app_password`. Use a Gmail App Password, not your main password.

**6. Configure Razorpay** — for payment processing in production, obtain API keys from the Razorpay dashboard and set `RAZORPAY_KEY_ID` and `RAZORPAY_SECRET`.

**7. For production**, set `FLASK_ENV=production`, `JWT_COOKIE_SECURE=true`, and provide a PostgreSQL `DATABASE_URL`. Do not run with `SEED_ON_START=true` in production after the first launch — set `SEED_ON_START=false` or `ALLOW_RESEED=false` thereafter.

---

## 18. How to Run the Project

**Development server**
```bash
source venv/bin/activate
python run.py
```
Access the application at http://localhost:5000

**With Gunicorn (local production-like)**
```bash
gunicorn -c deployment/gunicorn.conf.py run:app
```
Access at http://localhost:8000

**With Docker Compose**
```bash
cd deployment
docker-compose up --build
```
Access at http://localhost:8000

**Running database migrations only**
```bash
flask db upgrade
```

**Running seeds manually**
```bash
SEED_ON_START=true python run.py
```

---

## 19. Usage Instructions

**Login** — navigate to `/auth/login`. Use the seeded admin account (check `seed_users.py` for credentials) or register a new account.

**Dashboard** — the main dashboard shows fleet-wide machine status, unresolved alert count, average health score, and a summary of recent AI analyses. The view adapts based on the logged-in user's role.

**Adding a machine** — go to Machines → Add Machine. Fill in machine name, type, code, plant, department, installation date, cost per hour, and revenue per hour. Save. The machine detail page will show its API token.

**Sending test data** — with the machine API token, send a POST request:
```bash
curl -X POST http://localhost:5000/api/v1/data-ingest \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: <machine_api_token>" \
  -d '{
    "machine_id": 1,
    "timestamp": "2026-03-15T10:00:00",
    "temperature": 72.5,
    "vibration": 3.2,
    "current": 28.0,
    "voltage": 415.0,
    "pressure": 185.0,
    "humidity": 48.0,
    "speed": 1450.0,
    "running_status": true
  }'
```

**Viewing live data** — go to Machines → select a machine → Live View. Charts refresh automatically.

**AI Insights** — go to AI Insights from the navigation to see health scores, risk levels, anomaly detections, and maintenance suggestions per machine.

**Digital Twin** — go to Digital Twin from the navigation. Select a machine, configure simulation parameters (overload percentage, production surge percentage, sensor drift percentage), and click Simulate to see the impact on OEE, health, failure probability, and energy efficiency.

**Alerts** — the alert bell in the navigation shows unread alert count. Go to Alerts to see all open alerts, acknowledge them, or mark them resolved.

**Reports** — generate PDF or Excel reports from the Reports section. Executive reports include AI-generated narratives.

**Admin panel** — accessible to SUPER_ADMIN and ENTERPRISE_ADMIN roles from the navigation. Manage users, assign roles, and manage companies.

---

## 20. Code Architecture Explanation

The application follows a clean layered architecture:

**Presentation layer** — Jinja2 HTML templates with embedded Tailwind-style CSS and JavaScript. JS files make AJAX calls to REST API endpoints and render Chart.js visualisations. No frontend framework is used; vanilla JS keeps the stack simple and fast.

**Blueprint layer** — Flask blueprints group related routes into logical modules. Each blueprint has its own `__init__.py`, `routes.py`, and optionally `forms.py`. Blueprints are registered in the application factory.

**Service layer** — business logic is kept out of route handlers and placed in service modules. Route handlers validate inputs, call service functions, and render responses. Services are plain Python functions/classes with no HTTP awareness.

**AI layer** — deliberately isolated in `app/ai/`. The Gemini client, prompt templates, and worker thread are all contained within this package. The rest of the application interacts with AI via `enqueue_ai_job()` and reads results from the `AiAnalysis` and `AIPrediction` tables.

**Model layer** — SQLAlchemy declarative models with explicit relationships, indexes, and constraints. Models are kept clean — only database structure and simple property methods. No business logic in models.

**Seed layer** — the 40+ seed scripts create realistic demo data in a deterministic, ordered manner. The `SeedRunner` class tracks which seeds have run (via a `seed_metadata` table) and skips already-executed seeds unless `ALLOW_RESEED=true`.

**Scheduler** — APScheduler runs within the Flask application thread. Jobs use lambda wrappers to pass the app object into each function so they can push their own application context.

---

## 21. API Integrations

### Data Ingestion API

**POST `/api/v1/data-ingest`**
Headers: `X-API-KEY: <machine_token>`, `Content-Type: application/json`
Body fields: `machine_id` (int), `timestamp` (ISO 8601 string), `temperature` (float), `vibration` (float), `current` (float), `voltage` (float), `pressure` (float), `humidity` (float), `speed` (float), `running_status` (boolean)
Response 201: `{"status": "success", "message": "data stored"}`

**POST `/api/v1/heartbeat`**
Headers: `X-API-KEY: <machine_token>`
Response 200: `{"status": "success", "message": "heartbeat received", "last_seen": "..."}`

### Alert API

**GET `/api/v1/alerts`** — list alerts with optional filters (severity, status, plant, date range)
**POST `/api/v1/alerts/<id>/acknowledge`** — acknowledge an alert
**POST `/api/v1/alerts/<id>/resolve`** — resolve an alert

### KPI API

**GET `/api/v1/kpi/<machine_id>`** — retrieve KPI time series for chart rendering

### Digital Twin API

**POST `/api/v1/twin/run`** — submit a simulation scenario; returns simulation result and AI assessment
**GET `/api/v1/twin/history/<machine_id>`** — retrieve past simulation history

### RCA API

**POST `/api/v1/rca/generate`** — trigger AI root cause analysis for an alert group

### Google Gemini Integration

The application integrates with Google Gemini 2.5 Flash through the `google-genai` Python SDK. Every AI call includes a `GoogleSearch` grounding tool that Gemini can use when external knowledge is needed. The application constructs structured JSON prompts, sends them to Gemini, and parses the strictly-JSON response back into Python dictionaries.

All Gemini calls go through `app/services/gemini_service.py` which wraps the call with configurable retry logic (`GEMINI_MAX_RETRIES`, default 2) and timeout handling (`GEMINI_TIMEOUT_SECONDS`, default 20).

### Razorpay Payment Integration

Subscription purchases create a Razorpay order via the Razorpay Python SDK. The client-side Razorpay checkout collects payment. On return, the server verifies the payment signature using HMAC-SHA256 before activating the subscription. Transaction records store the Razorpay payment ID and subscription ID for reconciliation.

---

## 22. Hardware Components Used

Machine Monitoring is designed to work with real industrial machinery instrumented with the following hardware components. The platform supports any sensor node capable of making HTTP POST requests over a network connection.

**Temperature Sensors**
Type: PT100 RTD (Resistance Temperature Detector) or NTC thermistor probes.
Purpose: Monitor motor winding temperature, bearing temperature, coolant temperature, and ambient temperature inside control panels. The system tracks readings in degrees Celsius and alerts when values exceed calibrated thresholds (example: 85°C for a CNC lathe spindle bearing).
Typical range: 20°C to 85°C depending on machine type.

**Vibration Sensors (Accelerometers)**
Type: Piezoelectric accelerometer or MEMS accelerometer (e.g., ADXL345), measuring in mm/s RMS.
Purpose: Detect bearing wear, imbalance, looseness, misalignment, and gear mesh defects. Vibration is the most important early-warning indicator for rotating machinery. The system tracks vibration in mm/s and uses z-score analysis to detect statistical anomalies.
Typical range: 0.2 mm/s (good) to 15 mm/s (critical) depending on machine class.

**Current Transformers (CT)**
Type: Split-core current transformers (e.g., SCT-013 series), measuring in Amperes.
Purpose: Non-invasive measurement of motor current draw. Increased current at constant load indicates bearing deterioration, winding insulation degradation, or increased friction. Current together with voltage is also used to calculate real power consumption for energy and ESG analytics.
Typical range: 5 A to 65 A for industrial motors.

**Voltage Sensors**
Type: Differential voltage divider circuits or Hall-effect voltage transducers, measuring in Volts.
Purpose: Monitor supply voltage stability. Voltage sags or surges can damage motor insulation and indicate grid quality issues. Combined with current, calculates apparent power (VA) and energy consumption (kWh) for the ESG dashboard.
Typical range: 360 V to 430 V (3-phase industrial supply).

**Pressure Transducers**
Type: Piezoresistive or capacitive pressure transducers with 4–20 mA output.
Purpose: Monitor hydraulic circuit pressure, pneumatic supply pressure, coolant pressure, and lubrication oil pressure. Low pressure triggers lubrication failure alerts; high pressure indicates blockages.
Typical range: 120 bar to 260 bar (hydraulic press applications).

**Humidity Sensors**
Type: Capacitive humidity sensors (e.g., DHT22 or SHT31), measuring in %RH.
Purpose: Monitor ambient humidity inside electrical panels and machine enclosures. High humidity accelerates corrosion and electrical insulation degradation. Particularly important for packaging machines in food manufacturing environments.
Typical range: 35%RH to 70%RH.

**Speed / RPM Sensors**
Type: Inductive proximity sensors, optical encoders, or tachometers mounted on shaft collars.
Purpose: Monitor spindle speed, conveyor belt speed, and motor RPM. Speed deviations from setpoint indicate load changes, belt slip, or control system issues. Speed data serves as a throughput proxy for the ESG energy-per-unit calculation.
Typical range: machine-dependent (CNC spindle: 0–6000 RPM, conveyor: 0–120 RPM).

**Edge Computing Device / Microcontroller**
Type: Raspberry Pi 4 (preferred for Python-based nodes), Arduino Mega with Ethernet shield, or industrial-grade PLC with REST API capability (e.g., Siemens S7 with OPC-UA bridge).
Purpose: The edge device reads raw signals from all connected sensors through its ADC or digital inputs, applies calibration coefficients, formats the data as a JSON payload, and sends it to the platform every 5 seconds (configurable). It also sends heartbeat pings every 30 seconds to maintain online status.

---

## 23. Hardware Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         PHYSICAL MACHINE                                │
│                                                                         │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────────┐  │
│  │ PT100/NTC    │  │ Piezoelectric │  │  Split-Core CT Sensor      │  │
│  │ Temperature  │  │ Accelerometer │  │  (Non-invasive current)    │  │
│  │ Probe        │  │ (vibration)   │  │                            │  │
│  └──────┬───────┘  └──────┬────────┘  └────────────┬───────────────┘  │
│         │                 │                         │                  │
│  ┌──────▼─────────────────▼─────────────────────────▼───────────────┐ │
│  │              Signal Conditioning / ADC Board                      │ │
│  │     (amplification, filtering, 12-bit A/D conversion)            │ │
│  └────────────────────────────┬──────────────────────────────────────┘ │
│                               │ I2C / SPI / UART                       │
│  ┌────────────────────────────▼──────────────────────────────────────┐ │
│  │              EDGE DEVICE (Raspberry Pi / Arduino / PLC)           │ │
│  │                                                                   │ │
│  │   Sensor polling (every 5s)                                      │ │
│  │   Calibration coefficient application                            │ │
│  │   JSON serialisation                                             │ │
│  │   HTTP POST to /api/v1/data-ingest with X-API-KEY                │ │
│  │   HTTP POST to /api/v1/heartbeat every 30s                       │ │
│  └────────────────────────────┬──────────────────────────────────────┘ │
└───────────────────────────────│─────────────────────────────────────────┘
                                │ Ethernet / WiFi / 4G LTE
                                ▼
                   ┌─────────────────────────┐
                   │   Plant Network / VPN   │
                   └─────────────┬───────────┘
                                 │
                                 ▼
                   ┌─────────────────────────┐
                   │  Machine Monitoring     │
                   │  Web Application        │
                   │  (Flask / Gunicorn)     │
                   └─────────────────────────┘
```

**Communication protocol** — plain HTTPS with token-based authentication. No specialised IoT protocols (MQTT, OPC-UA) are required, though an edge device bridge can translate from those protocols.

**Network topology** — machines can be on a local plant network reaching the server via internal LAN or VPN, or they can push data directly over 4G/LTE if the server is hosted on a public cloud.

**Data security** — each machine has its own unique 43-character URL-safe random API token (`secrets.token_urlsafe(32)`). Tokens are stored in the database and matched on every ingestion request. If a token is compromised, it can be regenerated from the admin interface.

---

## 24. Hardware Setup Instructions

**Step 1 — Install sensors on the machine**
Mount the vibration accelerometer on the motor casing or bearing housing using a flat-faced stud mount for optimal coupling. Attach temperature probes to bearing housings and windings using thermal adhesive or compression clamps. Install current transformers around the power supply cables (split-core type requires no electrical interruption). Mount the pressure transducer on a tee fitting in the hydraulic or pneumatic line. Place the humidity sensor inside the control panel enclosure away from direct heat sources.

**Step 2 — Wire sensors to the edge device**
Connect sensor signal outputs to the edge device's ADC inputs or I2C/SPI ports according to the sensor datasheet. Use shielded cable for analog signal runs longer than 30 cm to prevent electromagnetic interference from motor drives.

**Step 3 — Configure the edge device firmware**
Create a configuration file on the Raspberry Pi (or equivalent) containing:
```json
{
  "machine_id": 1,
  "api_token": "your_machine_api_token",
  "server_url": "https://your-monitoring-server.com/api/v1",
  "ingest_interval_seconds": 5,
  "heartbeat_interval_seconds": 30,
  "sensors": {
    "temperature_channel": 0,
    "vibration_channel": 1,
    "current_channel": 2,
    "voltage_channel": 3,
    "pressure_channel": 4,
    "humidity_i2c_address": "0x44"
  },
  "calibration": {
    "temperature_offset": 0.5,
    "current_multiplier": 1.0
  }
}
```

**Step 4 — Write or deploy the data posting script**
A minimal Python script on the Raspberry Pi polls all sensors and posts to the platform:
```python
import time
import json
import requests
from datetime import datetime

CONFIG = json.load(open("config.json"))

while True:
    payload = {
        "machine_id": CONFIG["machine_id"],
        "timestamp": datetime.utcnow().isoformat(),
        "temperature": read_temperature(),
        "vibration": read_vibration(),
        "current": read_current(),
        "voltage": read_voltage(),
        "pressure": read_pressure(),
        "humidity": read_humidity(),
        "speed": read_speed(),
        "running_status": True
    }
    try:
        requests.post(
            f"{CONFIG['server_url']}/data-ingest",
            headers={"X-API-KEY": CONFIG["api_token"]},
            json=payload,
            timeout=5
        )
    except Exception as e:
        print(f"Send error: {e}")
    time.sleep(CONFIG["ingest_interval_seconds"])
```

**Step 5 — Test the connection**
Send a manual curl request (see Usage Instructions) and verify that the machine's Live View in the dashboard shows the reading.

**Step 6 — Configure sensor thresholds**
In the web interface, navigate to the machine, open sensor management, and set the min/max thresholds based on the machine manufacturer's specifications and your operational experience.

---

## 25. Hardware-Software Interaction

The hardware-software boundary is defined entirely by the REST API at `/api/v1/data-ingest`. The platform has no knowledge of hardware protocols, physical wiring, or sensor electronics — it only knows about the JSON payload it receives.

**Authentication handshake** — the edge device includes the `X-API-KEY` header in every request. The Flask route handler calls `Machine.query.filter_by(api_token=token).first()` to authenticate and identify the machine. If the token is invalid, the request is rejected with HTTP 401.

**Data normalisation** — all sensor values arrive as floating-point numbers in engineering units (°C, mm/s, A, V, bar, %RH, RPM). The edge device is responsible for applying calibration coefficients before transmission. The platform stores raw received values.

**Heartbeat mechanism** — when a machine is running but not producing (idle, warming up), the edge device continues sending heartbeat pings every 30 seconds to the `/api/v1/heartbeat` endpoint so the platform does not mark it offline. The scheduler job checks `last_seen` every minute and transitions machines to `offline` if no message has been received in 2 minutes.

**Alert feedback loop** — the platform does not send commands back to the machine hardware. All responses to alerts are human-driven through the maintenance workflow (technician receives email, acknowledges alert in platform, performs physical intervention). This is an intentional safety boundary — the platform is a monitoring and intelligence layer, not an industrial control system.

**Simulation mode** — in development (`SIMULATION_MODE=true`), the platform can call its own data ingestion endpoint internally using configured machine tokens, simulating sensor readings without real hardware. The simulation ingest interval is configurable via `SIM_INGEST_INTERVAL_SECONDS`.

---

## 26. Real World Implementation

Machine Monitoring is designed for implementation across a range of industrial manufacturing contexts. Based on the seeded demo data and the machine types coded into the seeds, the following real-world scenarios apply directly:

**CNC Machining (CNC Lathe, Milling Machine)** — temperature and vibration sensors detect spindle bearing wear, tool chatter, and coolant system degradation. Current monitoring catches tool breakage (current spike) and spindle overload. The predictive service estimates remaining useful life of bearings based on vibration trend slope.

**Hydraulic Press** — pressure transducers monitor hydraulic circuit integrity. Vibration sensors detect pump cavitation and valve chattering. Temperature monitoring catches hydraulic oil degradation and seal leakage (heat build-up from internal leakage).

**Packaging Machine** — humidity sensors protect electronic drives from moisture ingress. Temperature monitors detect conveyor motor overheating. Speed sensors detect belt slip and jam events.

**Multi-plant manufacturing company** — the platform supports a head office overseeing plants in different cities. The CEO dashboard shows cross-plant OEE comparisons, fleet health heatmaps, and consolidated financial exposure from downtime. Each plant's data is isolated by company/plant scoping.

**Maintenance team workflow** — when a vibration alert fires at 03:00, the on-call technician receives an email with the alert details, machine location, and AI-generated maintenance suggestion. They acknowledge the alert on their mobile browser, add a timeline note, and schedule a bearing inspection for the next day. The platform tracks resolution time for SLA compliance reporting.

**Energy management** — the ESG dashboard calculates daily kWh consumption from voltage/current readings. Plant managers can see which machines consume the most energy, compare energy-per-unit-produced across production runs, and track carbon proxy metrics against sustainability targets.

---

## 27. Data Flow Explanation

```
SENSOR READING
     │
     ▼
POST /api/v1/data-ingest
     │ (X-API-KEY auth)
     ▼
Token validation → Machine lookup
     │
     ▼
MachineData row created
Machine.last_seen updated
Machine.status = running/idle
     │
     ├──────────────────────────────────────────────────────────┐
     │                                                          │
     ▼                                                          ▼
evaluate_alerts_for_datapoint()                    enqueue_ai_job(data_id)
     │                                                          │
     ▼                                                          ▼
Compare readings to sensor thresholds          AI Worker Thread dequeues job
     │                                                          │
  Breach?                                                       ▼
     │ yes                                           run_ai_analysis(data_point)
     ▼                                                          │
Create Alert record                                             ▼
Assign severity + SLA deadline                        Build Gemini prompt
Send email notification                                (snapshot + 24h summary)
     │                                                          │
     ▼                                                          ▼
Alert in database                                     Call Gemini 2.5 Flash
                                                               │
                                                               ▼
                                                    Parse JSON response
                                                               │
                                                               ▼
                                                    Save AiAnalysis record
                                                    (health_score, risk_level,
                                                     anomaly, suggestion)


EVERY 30 MINUTES (Scheduler)
     │
     ▼
run_scheduled_predictions()
     │
     ├── failure_probability_prompt → Gemini → AIPrediction.failure_probability
     ├── rul_estimation_prompt → Gemini → AIPrediction.remaining_hours
     ├── degradation_analysis_prompt → Gemini → AIPrediction.degradation_trend_score
     └── preventive_action_prompt → Gemini → AIPrediction.preventive_actions


EVERY MINUTE (Scheduler)
     │
     ├── Check last_seen < now - 2min → mark machine offline → AuditLog
     └── Check open alerts past SLA deadline → escalate → send email


NIGHTLY 02:15 UTC (Scheduler)
     │
     └── Aggregate MachineData → MachineStats (hourly/daily averages)
```

---

## 28. Security Considerations

**Authentication layers** — web sessions use Flask-Login with Bcrypt-hashed passwords and CSRF-protected forms. REST API endpoints use JWT access tokens (15-minute lifetime) or machine API tokens (long-lived, per-device). Machine tokens are generated with `secrets.token_urlsafe(32)` (256 bits of entropy).

**JWT token blacklisting** — when a user logs out, their access token JTI is written to the `token_blacklist` table. All JWT requests check this blacklist via the `check_if_token_revoked` loader.

**CSRF protection** — Flask-WTF's `CSRFProtect` is active globally. API endpoints that are called by external devices use `@csrf.exempt` but require the machine API token instead.

**Role-based access control** — every sensitive route is decorated with `@role_required()`, `@manager_required()`, or `@admin_required()`. Plant-scoped routes additionally check `@plant_scope_required`.

**Multi-tenancy isolation** — all database queries include `company_id` scoping. The `DevBypassQuery` class that can bypass this is only active when `DEV_SHOW_ALL_USERS_DATA=true`, which defaults to `true` only in `DevelopmentConfig`.

**Subscription enforcement** — the `enforce_subscription_guard` before-request hook checks subscription status on every authenticated request. If the subscription is inactive, non-admin users are logged out immediately.

**Rate limiting** — configurable rate limits (default 120 requests/minute, burst 200) are tracked in the database per API key via the `@rate_limit` decorator.

**Session security** — `SESSION_COOKIE_HTTPONLY=True` prevents JavaScript access to session cookies. `REMEMBER_COOKIE_HTTPONLY=True` and `REMEMBER_COOKIE_DURATION=14 days` for persistent logins. In production, `SESSION_COOKIE_SECURE=True` ensures cookies are only sent over HTTPS.

**Audit logging** — role changes, machine management actions, and alert resolutions are all written to an immutable audit log with actor ID, IP address, and before/after values.

**Email and Razorpay** — Razorpay payment signatures are verified with HMAC-SHA256 before activating subscriptions. Email passwords and API keys are never hardcoded — they are loaded from environment variables.

---

## 29. Performance Considerations

**Database indexes** — all high-frequency query patterns are indexed. `machine_data` has a compound index on `(machine_id, timestamp)`. `alerts` is indexed on machine, plant, company, status, severity, and created_at. `ai_analysis` is indexed on `(machine_id, timestamp)`.

**Background processing** — AI analysis is done asynchronously in a worker thread, so data ingestion responses are always fast (< 50ms) even when Gemini calls take several seconds.

**Result caching** — report data is cached in-process with a configurable TTL (`CACHE_DEFAULT_TTL_SECONDS=300` for general data, `REPORT_CACHE_TTL_SECONDS=900` for report data) to avoid repeated expensive database aggregations.

**Nightly aggregation** — raw sensor readings are aggregated into hourly and daily stats tables nightly. Dashboard charts read from these aggregated tables rather than scanning the full `machine_data` table, making chart rendering fast even with months of data.

**Gunicorn threading** — the production Gunicorn configuration uses `gthread` workers with 4 threads each. This means I/O-bound operations (database queries, Gemini API calls) can proceed concurrently within each worker without blocking.

**Pagination** — alert lists, machine lists, and report lists are paginated to prevent large query result sets from being loaded entirely into memory.

---

## 30. Scalability Discussion

**Vertical scaling** — the Gunicorn configuration automatically sets `cpu_count * 2 + 1` workers, so adding CPU cores to the application server immediately improves throughput.

**Database scaling** — for production workloads with many machines sending data every 5 seconds, SQLite will quickly become a bottleneck. PostgreSQL is the recommended production database. For very high data volumes (100+ machines), partitioning the `machine_data` table by month is advisable.

**Horizontal scaling** — the application can run as multiple Gunicorn instances behind a load balancer, but APScheduler currently runs in-process. In a multi-instance deployment, the scheduler should be moved to a dedicated worker process or replaced with Celery + Redis to avoid duplicate job execution.

**AI workload scaling** — the AI worker thread is a single daemon thread per application instance. Under high load (many machines sending data simultaneously), the queue depth will grow. A natural extension is to move AI job processing to Celery workers, allowing the number of AI processing workers to scale independently of the web tier.

**Multi-tenancy scaling** — the company/plant/machine hierarchy allows adding new tenants without any schema changes. Row-level security at the application layer (rather than database level) keeps the implementation simple for the current scale.

---

## 31. Future Improvements

**MQTT support** — adding an MQTT broker (Mosquitto) alongside the HTTP API would allow lower-overhead, lower-latency sensor communication, which is preferred by embedded sensor nodes with limited compute.

**OPC-UA integration** — many industrial PLCs and SCADA systems speak OPC-UA. An OPC-UA adapter service that reads tags and posts to the data ingestion API would enable integration with legacy industrial infrastructure.

**Mobile app** — a React Native or Flutter mobile app for maintenance technicians would allow alert acknowledgement, task completion, and machine status checks from the shop floor without opening a browser.

**Celery task queue** — replacing the in-process AI worker thread with Celery + Redis would allow scaling the AI analysis pipeline independently and provide task retry, monitoring, and rate limiting.

**WebSocket real-time streaming** — replacing the polling-based live view with a WebSocket connection would deliver lower-latency updates to the browser and reduce HTTP overhead.

**Predictive maintenance ML models** — the current predictive analysis relies entirely on Gemini. Training domain-specific LSTM or transformer models on the accumulated sensor history would provide faster, lower-cost predictions for common failure modes.

**Multi-language support** — internationalisation (i18n) using Flask-Babel would allow the platform to serve operators in their native language — important for global manufacturing clients.

**SSO/SAML integration** — enterprise customers typically require Single Sign-On via SAML 2.0 or OAuth 2.0 with their corporate identity provider.

**Grafana integration** — exposing a Prometheus metrics endpoint would allow integration with Grafana for customised monitoring dashboards and alerting rules.

**Geospatial plant view** — a map-based overview of all plants with health status indicators would be valuable for companies with geographically distributed facilities.

---

## 32. Limitations

**Single AI thread** — the current implementation uses a single background worker thread for AI analysis. Under burst data ingestion from many machines simultaneously, AI analysis results may lag behind real-time readings.

**In-process cache** — the cache service uses a simple Python dictionary. It does not survive application restarts and is not shared across multiple Gunicorn worker processes. For production multi-worker deployments, Redis or Memcached should be used.

**No real-time WebSocket** — live dashboards poll the server every few seconds rather than receiving push updates. This creates a small latency gap between actual machine state and displayed state.

**SQLite limitations** — the default SQLite database is not suitable for production workloads with concurrent writes from multiple machines. PostgreSQL must be used for any deployment with more than a handful of machines.

**Simulation mode limitations** — the built-in simulation generates synthetic sensor readings. Real machines exhibit complex, non-linear failure modes that simple simulation cannot replicate fully.

**Gemini API dependency** — the AI analysis pipeline depends on Google Gemini availability. If the Gemini API is down or rate-limited, AI analysis jobs will fail after the configured number of retries and be marked with `status=failed`.

**No command-and-control** — the platform is read-only from a hardware perspective. It cannot send setpoints, alarms, or control signals back to machines. Any corrective action requires a human maintenance technician.

---

## 33. Troubleshooting Guide

**Application does not start — `ModuleNotFoundError`**
Ensure the virtual environment is activated (`source venv/bin/activate`) and that `pip install -r requirements.txt` completed without errors.

**`flask db upgrade` fails with "Target database is not up to date"**
Run `flask db stamp head` to mark the current state as up to date, then re-run `flask db upgrade`.

**AI analysis always shows `status=failed`**
Check that `GEMINI_API_KEY` is set correctly in `.env`. Verify the key is valid by testing it directly at https://aistudio.google.com/. Check the application logs for the specific Gemini error message.

**Machine shows as `offline` immediately after data ingestion**
The offline monitor checks `last_seen < now - 2 minutes`. If the machine clock is significantly behind UTC, the `last_seen` timestamp may appear old. Ensure the edge device uses NTP to synchronise its clock to UTC.

**Data ingestion returns HTTP 401 `Invalid API token`**
Copy the API token exactly from the machine detail page in the web interface. The token is case-sensitive. If it was regenerated, update the token in the edge device configuration.

**No emails are being sent**
Check `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, and `MAIL_PASSWORD` in `.env`. For Gmail, ensure you are using an App Password (not your Gmail account password). Check the application logs for SMTP error messages.

**Gunicorn `worker timeout`**
If Gemini API calls are taking longer than 120 seconds, increase the `timeout` value in `deployment/gunicorn.conf.py`. The current default is 120 seconds.

**Seeds run every time the application starts**
Set `SEED_ON_START=false` or `ALLOW_RESEED=false` in `.env` to prevent the seed runner from executing on every startup after the first successful seed run.

**Dashboard shows no data after login**
If the active company is not set, queries may return empty results. Log in as a SUPER_ADMIN and use the company switcher in the navigation to select the active company.

---

## 34. Frequently Asked Questions

**Q: Can the platform monitor machines from different manufacturers?**
A: Yes. The platform is hardware-agnostic. Any machine that has an edge device capable of making HTTP POST requests can send data. The machine type, manufacturer, and model are stored as metadata fields.

**Q: How many machines can the platform handle?**
A: On a reasonably sized cloud VM (4 vCPUs, 8 GB RAM, PostgreSQL), the platform can comfortably handle 50–100 machines sending data every 5 seconds. For larger deployments, the AI worker should be moved to Celery and PostgreSQL should be sized accordingly.

**Q: Is the Gemini API usage billed per call?**
A: Yes, Google Gemini API calls are billed based on token usage. Each predictive maintenance refresh triggers up to four Gemini calls per machine. With the default 30-minute refresh interval, 10 machines would generate approximately 192 Gemini calls per day.

**Q: Can I use a different AI model instead of Gemini?**
A: The AI layer is isolated in `app/ai/gemini_engine.py` and `app/services/gemini_service.py`. To use a different model, implement the same function signatures with a different client library. The rest of the application only calls these functions and does not depend on Gemini-specific types.

**Q: How is data security handled for multi-tenant deployments?**
A: All database queries include a `company_id` filter applied at the service and route level. Users can only see data belonging to their company. The `DevBypassQuery` that relaxes this scoping is disabled by default in `ProductionConfig`.

**Q: What happens if the Gemini API is unavailable?**
A: The AI worker will retry up to `GEMINI_MAX_RETRIES` times (default 2) with exponential backoff. After all retries are exhausted, the analysis record is marked `status=failed`. The application continues to function normally — data ingestion, alerts, and dashboards work without AI analysis. When Gemini becomes available again, new data points will trigger new analysis jobs.

**Q: Can I add custom sensor types?**
A: The current sensor configuration supports temperature, vibration, current, voltage, pressure, humidity, and speed. To add a new type, add the new field to the `MachineData` model, create a migration, and update the ingestion endpoint to read the new field.

**Q: How do I reset the database and re-seed?**
A: Delete the `instance/app.db` file (SQLite) or drop and recreate the PostgreSQL database, then run `flask db upgrade` followed by `python run.py` with `SEED_ON_START=true`.

---

## 35. Contribution Guidelines

**Code style** — follow PEP 8 for Python. Use type hints on all function signatures. Import order: stdlib, third-party, local imports separated by blank lines.

**Blueprint conventions** — new features should be added as new blueprints with their own `routes.py` and (if needed) `forms.py`. Register the blueprint in `app/__init__.py`.

**Service layer** — business logic must not live in route handlers. Create or extend service modules in `app/services/`. Route handlers should be thin wrappers that call service functions.

**Model changes** — any change to a model must be accompanied by a Flask-Migrate migration script. Never modify existing migration scripts; always create new ones.

**AI prompt changes** — all Gemini prompt strings live in `app/ai/prompt_templates.py`. Prompt changes should be tested against a live Gemini API instance to verify the JSON schema is still respected.

**Testing** — write tests in a `tests/` directory using `pytest`. Unit-test service functions. Integration-test API endpoints using Flask test client.

**Pull requests** — keep PRs focused on a single concern. Include a description of the change, the testing performed, and any migration steps required.

---

## 36. Version Control Strategy

**Branch strategy** — use `main` as the stable production branch. Feature branches should be named `feature/<description>`, bug fixes `fix/<description>`, and hotfixes `hotfix/<description>`.

**Commit messages** — use the imperative mood: "Add digital twin simulation engine", "Fix alert SLA calculation". Reference issue numbers where applicable.

**Migrations** — database migration scripts generated by `flask db migrate` should be committed in the same PR as the model change that required them. Migration scripts must never be modified after they have been applied to any environment.

**Release tagging** — tag production releases with semantic version numbers: `v1.0.0`, `v1.1.0`.

**Secrets** — never commit `.env` files, API keys, or secrets. The `.gitignore` already excludes `.env`. The `.env.example` file is the canonical reference for all required environment variables.

---

## 37. Testing Strategy

**Unit tests** — test individual service functions in isolation using pytest with a mock SQLAlchemy session. Focus on: threshold evaluation logic in `alert_service`, simulation math in `simulation_engine`, calibration date clamping in seed utilities, and JSON parsing in `gemini_engine`.

**Integration tests** — test complete request/response cycles using the Flask test client. Key scenarios: data ingestion with valid token, data ingestion with invalid token (expect 401), alert creation on threshold breach, JWT token issuance and blacklisting, and subscription enforcement redirect.

**AI tests** — mock the Gemini client to test prompt construction, JSON parsing edge cases (malformed response, missing fields), and `_coerce_response` normalisation logic without consuming API quota.

**Seed tests** — run the seed runner against a fresh in-memory SQLite database and assert all expected records were created without errors.

**Load testing** — use Locust or similar to simulate 20+ machines sending data every 5 seconds simultaneously. Measure ingestion response time (target < 100ms P95) and database write throughput.

---

## 38. Deployment Guide

**Docker Compose (single server)**
```bash
# Build and start
docker-compose -f deployment/docker-compose.yml up -d --build

# View logs
docker-compose -f deployment/docker-compose.yml logs -f

# Stop
docker-compose -f deployment/docker-compose.yml down
```

**Manual Gunicorn deployment**
```bash
source venv/bin/activate
export FLASK_ENV=production
flask db upgrade
gunicorn -c deployment/gunicorn.conf.py run:app
```

**Reverse proxy (Nginx) configuration**
Place Nginx in front of Gunicorn to handle SSL termination and static file serving:
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;

    location /static/ {
        alias /app/app/static/;
        expires 7d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Production checklist**
Set `FLASK_ENV=production`. Set strong values for `SECRET_KEY` and `JWT_SECRET_KEY`. Set `DATABASE_URL` to a PostgreSQL connection string. Set `JWT_COOKIE_SECURE=true`. Set `SEED_ON_START=false` after the first startup. Configure SMTP credentials for email notifications. Configure Razorpay keys for payment processing. Set up SSL certificates (Let's Encrypt is recommended). Run `flask db upgrade` before starting the application.

**Cloud deployment (AWS, GCP, Azure)**
The Docker image can be pushed to any container registry and deployed on AWS ECS, Google Cloud Run, or Azure Container Instances. Use a managed PostgreSQL service (RDS, Cloud SQL, Azure Database for PostgreSQL) for the database. Store environment variables in the cloud provider's secret manager rather than a `.env` file.

---

## 39. License Section

This project is provided as a portfolio and demonstration codebase. The license terms should be specified by the repository owner. Before using this code in a commercial product, ensure you comply with the licenses of all dependencies, particularly:

The `google-genai` SDK is subject to Google's Terms of Service and the Gemini API usage policies.
The `razorpay` SDK is subject to Razorpay's Terms of Service.
All other Python dependencies carry their own OSI-approved licenses (MIT, BSD, Apache 2.0) as indicated in their respective PyPI package metadata.

---

## 40. Credits and Acknowledgments

**Google Gemini** — the AI capabilities of this platform are powered by Google Gemini 2.5 Flash, accessed through the official `google-genai` Python SDK.

**Flask ecosystem** — the project is built on Flask and the broad ecosystem of Flask extensions (Flask-Login, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF, Flask-JWT-Extended, Flask-Bcrypt, Flask-Mail) maintained by their respective open-source contributors.

**APScheduler** — background job scheduling is provided by the APScheduler library maintained by Alex Grönholm.

**Chart.js** — all frontend data visualisations use Chart.js, an open-source JavaScript charting library.

**ReportLab and openpyxl** — PDF and Excel export capabilities are provided by these mature open-source Python libraries.

**Razorpay** — payment processing integration via the Razorpay Python SDK and Razorpay payment gateway.

---

## 41. Conclusion

Machine Monitoring is a comprehensive, production-ready Industrial IoT platform that bridges the gap between physical manufacturing equipment and modern AI-driven operations intelligence. It takes the full journey — from raw sensor signals on the shop floor, through a secure cloud data pipeline, into a Google Gemini analysis engine, and out to executives, maintenance planners, and technicians through role-appropriate dashboards.

The architecture is deliberately layered and modular: hardware communicates over standard HTTP, the Flask blueprint structure keeps features independently maintainable, the service layer isolates business logic, and the AI layer is pluggable. The platform is equally at home running on a single developer laptop with SQLite and simulated sensor data, or on a production cloud server with PostgreSQL, Gunicorn multi-processing, and real machines sending live telemetry.

For manufacturing companies looking to move from reactive to predictive maintenance, reduce unplanned downtime, gain visibility into energy consumption and ESG metrics, and give executives a real-time operational picture across multiple plants — this platform provides a solid, extensible foundation to build on.

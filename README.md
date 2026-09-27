# CleanCity — Smart Waste Management and Monitoring System

A working B.Tech project covering the lifecycle from citizen report to verified cleanup, citizen confirmation and government oversight. The four roles are **CITIZEN**, **WASTE_COLLECTOR**, **SUPERVISOR**, and **GOVERNMENT_AUTHORITY**.

## Start the prepared local installation

Open `Start CleanCity.cmd` in this folder, then visit **http://127.0.0.1:8000**. If the server is already running, simply visit that address. Local demo accounts and randomly generated passwords are in **demo-access.txt**. The file is excluded from Git. All accounts are clearly labelled demo accounts.

PowerShell alternative, from this folder: `.\Start.ps1`. For a fresh installation, run `.\Setup.ps1` once first. Setup requires Python 3.11+ and Node 20.19+ or Node 22.12+. Setup installs locked dependencies, runs additive migrations, seeds local demo data and builds the interface. It does not erase data. If your Windows execution policy blocks scripts, use your organization's approved script-running policy; no script changes system execution policy.

The current machine has already been set up. There is no need to reinstall dependencies for the demonstration.

## Features

- Argon2 password hashing, revocable 8-hour opaque sessions, HttpOnly cookies, server-side role and object authorization.
- Citizen registration, profile editing and private complaint history; authority-controlled staff creation and activation.
- Configurable categories, wards/zones, priority SLA hours and collector availability.
- Waste streams: wet, dry, sanitary, special care, unknown/mixed. These are a project taxonomy, not a certification of regulatory compliance.
- Coordinate entry, map pin selection, optional browser geolocation, manually entered address, OpenStreetMap visualization.
- Explicit state transitions, optimistic locking, status and assignment history.
- Collector recommendations by same-ward eligibility and active workload.
- Validated and re-encoded photographic evidence, size/pixel caps, private authenticated reads, SHA-256 duplicate-image rejection.
- Fresh before/after evidence for reassignment, reopened and returned-work cycles.
- Configurable SLA deadlines; a worker checks warnings and escalation every minute.
- Citizen confirmation, bounded reopening and feedback.
- In-app notifications with read state; optional SMTP delivery outbox with bounded retries.
- Filterable real-data dashboards, ward/category/stream/status distributions, trends, service metrics, hotspot grid, collector counts and CSV exports.
- Audit trail for account, configuration, workflow and evidence changes.
- Responsive React interface with separate actions for each role.

## Technology and structure

| Directory | Purpose |
|---|---|
| `backend/` | FastAPI API, SQLAlchemy models, validation, authentication, workflow helpers, storage, email adapter, seed/bootstrap commands |
| `frontend/src/` | React + TypeScript UI, API client, Leaflet map and styles |
| `migrations/` | Alembic revisions 001 and 002 |
| `tests/` | Isolated API/workflow/security/migration tests |
| `docs/` | Architecture, database, security, API, workflow, testing, deployment and viva guide |
| `data/` | Local SQLite database, private evidence and server logs; excluded from Git |

Local development uses SQLite. PostgreSQL is the intended deployment database; its driver and Docker Compose configuration are included. Docker/PostgreSQL execution has not been validated on this machine because Docker is unavailable.

## Development commands

Run backend commands from the project root with the prepared environment:

- Migrate: `.venv/Scripts/python.exe -m alembic upgrade head`
- Demo seed: `.venv/Scripts/python.exe -m backend.seed`
- API: `.venv/Scripts/python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000`
- Tests: `.venv/Scripts/python.exe -m pytest -q`
- Python lint: `.venv/Scripts/python.exe -m ruff check backend migrations tests`
- Python formatting: `.venv/Scripts/python.exe -m ruff format --check backend migrations tests`

From `frontend/`: `npm run dev`, `npm run build`, `npm run typecheck`, `npm run lint`. Development requests are proxied to the backend by Vite; the built application is served by FastAPI under the same origin. Rebuild the frontend before serving a changed production UI.

API reference: **http://127.0.0.1:8000/docs** and **/openapi.json**. Mutating API clients must send `X-Requested-With: swm` and a valid session cookie. Swagger can display the schema; use the application or an API client with that header for mutation requests.

## Configuration and production

See `.env.example`. No map key or external email service is required for local use. Never use demo data or demo credentials in production. To initialize a fresh production database, migrate and run `python -m backend.bootstrap`, then sign in as the authority to create wards, categories and staff. Password entry is hidden and not accepted on the command line.

Use HTTPS, set `APP_ENV=production`, configure an exact `ALLOWED_ORIGINS`, use PostgreSQL, persistent evidence storage and database backups. Run one application worker because the email/escalation scheduler is embedded. See `docs/deployment.md` for limitations and deployment steps.

## Demonstration

Use the citizen account to create a report with a photo and map location. Supervisor: review, verify and assign. Collector: accept, upload before image, start, upload a different after image and submit completion. Supervisor: approve. Citizen: confirm and rate, or reopen with a reason. Authority: inspect analytics, map, reports and audit events.

Every chart queries database records; the seed creates one clearly labelled illustrative report, not invented municipal statistics. See `docs/demo-and-viva.md` for the detailed demonstration and explanation.

## Scope limits

This is a validated local project, not a claim of production certification. Native Android, SMS, cloud-object-storage adapters, automatic geocoding/official ward polygons, PDF reports and predictive AI/IoT are not implemented. They are optional extensions; the secure responsive web workflow is implemented. SMTP is implemented but no real delivery has been attempted without credentials. Analytics currently aggregate in memory and are intended for college-scale datasets. More operational limits are documented in the development report.

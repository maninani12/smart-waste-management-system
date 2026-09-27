# Development report — updated 27 September 2026

## A. Repository detected / resulting stack

The supplied workspace contained only empty work/output directories. No existing Smart Waste repository was supplied. A new project was created at `C:\Users\manik\OneDrive\Desktop\Smart-Waste-Management`, the actual Windows Desktop location. Other Desktop projects were not modified. A local Git repository was initialized; nothing was committed, pushed or published.

Result: Python 3.13, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic, Argon2, Pillow; React 19, TypeScript, Vite, Leaflet, Lucide; SQLite local database and PostgreSQL driver/container configuration. No native mobile project existed or was generated. Responsive web is supported.

## B. Original state

No application, schema, tests, frontend or startup configuration existed in the target directory. All implementation is new. The brief's inspect/preserve requirement was followed; no working repository was replaced.

## C. Implemented

- Four-role authentication, citizen-only registration, profiles, staff administration, activation and collector availability.
- Hashed passwords; opaque server sessions; expiry/logout; CSRF/origin checks; rate limiting; backend role and complaint-object scopes.
- Relational wards/zones, categories, SLA policy, complaints, assignments, history, evidence, feedback, notifications, audit, escalations and email delivery outbox.
- Full lifecycle from submitted report through review, verified classification, assignment, acceptance, work, resolution submission, supervisor approval, citizen confirmation and feedback.
- Supervisor rejection, work return, reassignment, citizen reopening with eligibility limits, explicit reasons and retained histories.
- Optimistic concurrency checks and transactions around operational changes.
- Secure photographic evidence with type/size/pixel validation, metadata stripping, re-encoding, private reads and content-hash reuse checks. Fresh evidence per work cycle.
- Manual coordinates/address, map selection, permission-based browser location and complaint maps.
- Same-ward workload recommendation algorithm and privacy-preserving Haversine duplicate warnings.
- Priority-based deadlines; configurable warning/second-level escalation timing; automatic one-minute worker; idempotent escalation records.
- Guaranteed in-app notifications and read/unread state; optional SMTP adapter with bounded retries and honest NOT_CONFIGURED/FAILED statuses.
- Filterable authority/supervisor dashboards, status/category/stream/ward distributions, trends, time metrics, SLA compliance, historical/current hotspots, collector counts, CSV exports and audit viewer.
- Responsive role-specific UI, loading/error/empty states, input labels, confirmations, image previews and mobile sign-out.
- Additive migrations, generated demo credentials, idempotent seed, production bootstrap, Windows setup/start files, Dockerfile and PostgreSQL Compose configuration.

## D. Improvements made during validation

There was no prior application to refactor. Review of the new implementation led to: frozen explicit initial migration rather than importing mutable runtime models; fresh evidence cycles when supervisors return work; prevention of self-deactivation; database version advancement on image upload; readable secondary-text contrast; mobile logout; environment-specific demo labels; optional email delivery isolated from operational commits. Initial syntax/import/format/CSS issues were corrected and relevant checks rerun.

## E. Tests actually run

See `docs/testing.md` for exact commands and outcomes. Final suite: **14 PASS**, including an API end-to-end lifecycle and adversarial authorization/workflow cases. Python lint, formatter check, Alembic schema-drift check, frontend type checking, build, ESLint and Python dependency consistency checks passed. npm audit reported zero vulnerabilities; pip-audit reported no known vulnerabilities for the pinned Python dependency set.

Browser validation now includes the complete four-role lifecycle for SWM-2026-1B343A5B: submission, complaint image, review, verification, assignment, acceptance, before/start/after evidence, completion submission, supervisor approval, citizen confirmation and feedback. Three explicitly labelled synthetic test fixtures were used; they do not represent a real cleanup. The report is CLOSED, its feedback is persisted, and authority metrics show two demo reports, one active, one closed and 100% SLA compliance for the single verified resolution. Additional checks covered insights, mobile 390×844 layout, inline confirmation cancellation and persistent success messages. An upstream Starlette/httpx test-adapter deprecation warning remains non-fatal.

## F. Security review

Controls: Argon2, hashed revocable sessions, HttpOnly/SameSite cookies, Secure in production, active-account checking, role/row scope, input whitelisting, CSRF checks, single-process login throttling, private sanitized image storage, safe SQLAlchemy queries, versioned writes and append-only API audit behavior. No fixed production password or real credential was added. Local generated demo credentials and data are ignored by Git.

Remaining operational concerns: production HTTPS/proxy configuration, shared perimeter limits, scalable task claiming, quotas, backup/restore verification and independent security review. Audit is not tamper-proof against database administrators. Image hashes do not prove authenticity. See `docs/security.md`.

## G. Database changes

Migration 001 creates 13 normalized operational/configuration tables with foreign keys, indexes and constraints. Migration 002 adds `notification_deliveries`, bringing the total to 14 application tables (plus Alembic's version table). Tests verify additive migration preserves existing data. No destructive migration or downgrade was performed. SQLite is initialized locally; PostgreSQL configuration is provided but runtime validation is not claimed.

## H. APIs

Implemented groups: auth, users, config, complaints, transitions, assignment recommendations/assignment, evidence, feedback, notifications, analytics, CSV reports, audit and health. OpenAPI is generated from code at `/openapi.json`; `/docs` provides the reference. See `docs/api_documentation.md` for role requirements, inputs, filters and error conventions.

## I. Frontend

Screens: login/register, overview, report waste, complaint list/detail/timeline/evidence, collector job actions, supervisor verification/assignment, maps/hotspots, insights/reports, notifications, authority people/configuration/audit, profile. Four roles share components but expose only their permitted actions. Every KPI derives from API/database results. The local seed and browser-check report are explicitly demo data.

## J. Documentation and files

Created README, architecture, database design/ER diagram, workflow/state diagram/algorithms, API guide, security review, deployment guide, test report, demonstration/viva guide and this development report. Significant code/configuration groups are `backend/`, `frontend/`, `migrations/`, `tests/`, locked dependencies, environment example, setup/start scripts and container configuration. All remain uncommitted for user review.

## K. Remaining items

| Classification | Item and reason |
|---|---|
| BLOCKED / NOT RUN | Docker/PostgreSQL runtime validation: Docker is not installed here. SQLite migration tests pass but are not a substitute. |
| BLOCKED / NOT EXTERNALLY VALIDATED | SMTP end-to-end delivery: no provider credentials supplied. Adapter and failure/retry behavior implemented and tested. |
| OPTIONAL FUTURE ENHANCEMENT / NOT IMPLEMENTED | Native Android app; responsive web is the implemented mobile experience. |
| OPTIONAL FUTURE ENHANCEMENT / NOT IMPLEMENTED | SMS, cloud-object-storage provider, automatic reverse geocoding and official ward polygons. Core operation uses in-app notifications, private local storage and manual/map coordinates. |
| OPTIONAL FUTURE ENHANCEMENT / NOT IMPLEMENTED | PDF reports; database-backed CSV meets the minimum reporting requirement. |
| OPTIONAL FUTURE ENHANCEMENT / NOT IMPLEMENTED | Multi-ward supervisor membership, route optimization, live collector GPS, category-specific/business-hours SLA calendars. The implemented policy is one ward per operational user, workload scoring and elapsed priority hours. |
| OPTIONAL FUTURE ENHANCEMENT / NOT RUN | Municipal-scale performance/accessibility/penetration testing and full browser/device matrix. |
| OPTIONAL FUTURE ENHANCEMENT | AI/ML and IoT; deliberately excluded without datasets/hardware. |

Analytics currently aggregate filtered complaints in application memory, suitable for college-scale datasets; collector metrics attribute current ownership and hotspots use a rounded coordinate grid. The application is a demonstrated local project, not a production-security certification.

## L. External configuration

Nothing external is required to run the prepared local demo. Internet is needed for map tiles. Production needs PostgreSQL connection details, HTTPS, exact allowed origin and persistent backed-up storage. Optional email needs SMTP host/port/from and credentials if required. Real municipal ward boundaries and geocoding would need a chosen provider/dataset. No external messages were sent and nothing was published.

## M. Run instructions

The app is running locally at **http://127.0.0.1:8000**. Open `demo-access.txt` inside the Desktop project for generated account credentials. To start it later, open `Start CleanCity.cmd`; `Start.ps1` is the PowerShell equivalent. `Setup.ps1` is provided for a fresh machine and has already been carried out through the equivalent validated steps here. Detailed exact development commands are in README.

## N. Demo instructions

Citizen reports and attaches evidence → supervisor reviews/verifies/assigns → collector accepts, uploads before image, starts, uploads after image, submits notes → supervisor approves → citizen confirms/rates or reopens → authority inspects actual metrics, hotspot map, CSV and audit. Use distinct photographs and the Riverside demo ward. See `docs/demo-and-viva.md` for the full sequence.

## O. Viva summary

The project addresses the gap between reporting waste and proving its resolution. A modular FastAPI/React system combines a relational model, four-role workflow, evidence integrity checks, geospatial duplicate warnings, deterministic workload assignment, deadline escalation and accountable verification. Security resides on the server, state changes are transactional/versioned, and analytics use actual operational records. Validation includes a complete API lifecycle and unauthorized variants. Future extensions are clearly separated from implemented behavior.

## Follow-up changes on 27 September

Fixed success and duplicate-warning messages being cleared during detail refreshes. Added dismissal controls and cleared messages on navigation/logout. New reports now default to Unknown/Mixed waste rather than assuming Wet. Replaced native browser confirmation dialogs with an inline confirmation group; both cancellation and final confirmation were verified. Final frontend build and lint passed. No backend changes, database reset, commit, push or publication occurred during this follow-up.

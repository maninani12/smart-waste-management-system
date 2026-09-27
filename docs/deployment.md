# Setup and deployment

## Local Windows demonstration

The prepared virtual environment, database and frontend build are already present. Use `Start CleanCity.cmd` (or `Start.ps1`) to serve the app on 127.0.0.1:8000. If this port is in use by the existing demo server, use that running instance rather than starting another. The prepared demo server writes `data/server.log` and `data/server-error.log`.

For another machine: install Python 3.11+ and supported Node, copy the project excluding `.venv`, `node_modules`, `data` and `demo-access.txt`, then run `Setup.ps1`. Fresh demo credentials are generated. Setup refuses the demo seed under APP_ENV=production. Never copy a local database or account file into a public repository.

## PostgreSQL and containers

`compose.yaml` defines PostgreSQL 17 and the application, with separate persistent database and evidence volumes. `POSTGRES_PASSWORD` must be supplied; no password default is embedded. For a development container demonstration, build/start Compose, migrate, and run the seed inside the app container. For production, use `APP_ENV=production`, terminate TLS at a configured reverse proxy and set the exact external origin. Bindings currently expose the app only on loopback.

The Dockerfile builds React in a Node stage, installs locked Python requirements and runs as a non-root user. Startup applies migrations before serving. **Docker and PostgreSQL runtime validation are NOT RUN on the current machine: Docker is not installed.** The checked SQLite migration tests do not substitute for PostgreSQL integration tests.

For a clean production database run `python -m alembic upgrade head`, then `python -m backend.bootstrap`. Bootstrap creates only the initial authority and default priority SLA rules. In the interface create wards, categories and operational accounts. Supervisor/collector accounts require an existing ward. Use an appropriately encoded DATABASE_URL if the password contains URL-reserved characters.

## Operational assumptions

- One application process/worker. Escalation and email jobs run within it every minute. A stopped app does not deliver notifications until restarted.
- SMTP uses STARTTLS with certificate verification. Set EMAIL_PROVIDER=smtp, SMTP_HOST, SMTP_PORT, SMTP_FROM and optionally SMTP_USERNAME/SMTP_PASSWORD. Missing configuration records NOT_CONFIGURED. Existing skipped items are not bulk resent automatically.
- Email attempts are at-least-once: a process crash after SMTP acceptance but before database commit could cause duplicate delivery. Use a dedicated queue with provider idempotency before a large rollout.
- SMS is optional and not implemented. Local storage is isolated behind LocalStorage; a cloud adapter is not implemented.
- Maps use OpenStreetMap tiles over HTTPS; follow the provider's usage requirements for a real deployment. No geocoder or official ward-boundary dataset is configured.
- SLA hours are elapsed UTC clock hours. Configure SLA_WARNING_HOURS and ESCALATE_AFTER_HOURS for warning/escalation policy; values should be positive.
- Back up the database and `data/evidence` together. Test restores before relying on them. No automated destructive downgrade, database reset, commit, push or publication is provided.
- The Desktop is under OneDrive on this machine. Treat the whole project directory as local development data that may be synced by the user's existing OneDrive configuration. Do not place real citizen data here without an approved storage policy.

## Troubleshooting

- Missing tables: run Alembic upgrade from the project root with the selected DATABASE_URL.
- Missing UI: run `npm run build` inside frontend, then restart the backend.
- Map tiles unavailable: use manual latitude/longitude and address; the complaint can still be submitted.
- Cookie absent over local HTTP with production enabled: use HTTPS for production, or development mode for a loopback-only demonstration.
- Mutation 403: check exact origin and X-Requested-With header. Do not disable CSRF checking.
- Conflict 409: refresh the complaint to obtain the current version.
- Work cannot be submitted: attach distinct before/after photos in the current cycle and add completion notes.

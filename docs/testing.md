# Validation performed

Backend validation date: 26 September 2026. Browser workflow and final frontend validation: 27 September 2026. Tests use isolated temporary SQLite databases and temporary evidence storage; they do not erase the demo database.

| Command | Result | Evidence |
|---|---|---|
| `.venv/Scripts/python.exe -m pytest -q` | PASS | 14 tests passed in 57.04 seconds |
| `.venv/Scripts/python.exe -m ruff check backend migrations tests` | PASS | All checks passed |
| `.venv/Scripts/python.exe -m ruff format --check backend migrations tests` | PASS | 15 files already formatted |
| `.venv/Scripts/python.exe -m alembic upgrade head` | PASS | Local database upgraded through 002 |
| `.venv/Scripts/python.exe -m alembic check` | PASS | No new upgrade operations detected |
| `.venv/Scripts/python.exe -m backend.seed` | PASS | Demo data and random local account credentials created |
| `.venv/Scripts/python.exe -m pip check` | PASS | No broken requirements found |
| `.venv/Scripts/python.exe -m pip_audit -r requirements.lock.txt --no-deps --disable-pip` | PASS | No known vulnerabilities found in the pinned dependency set |
| `npm run build` from frontend | PASS | TypeScript and Vite build completed; 1,625 modules transformed |
| `npm run typecheck` from frontend | PASS | tsc --noEmit exited 0 |
| `npm run lint` from frontend | PASS | ESLint exited 0 |
| `npm audit --audit-level=high` from frontend | PASS | Zero vulnerabilities reported, including development dependencies |

## Automated scenarios

1. Full workflow: login → complaint → image → supervisor verification → assignment → collector before/start/after → completion → supervisor approval → citizen confirmation → feedback → analytics/history/notifications.
2. IDOR and role restrictions for another citizen, unassigned collector and out-of-ward supervisor.
3. Citizen-only registration, invalid credentials, duplicate account, logout, CSRF origin/header protection.
4. Invalid state transitions, stale version conflict, wrong-ward assignment, missing evidence, malformed/executable/reused uploads, evidence read permissions.
5. Reopen reason and fresh work cycle enforcement.
6. SLA breach/escalation idempotence, duplicate proximity and privacy, filters/date validation, CSV output.
7. Notification ownership, account deactivation and prevention of self-deactivation.
8. Workload recommendation ordering and reassignment access revocation.
9. Missing and failed email providers preserve complaint state and record delivery status/retry.
10. Returned work cannot reuse prior-cycle evidence.
11. Fresh Alembic migration, additive upgrade preserving an inserted ward, repeatable upgrade.
12. Expired session and login attempt limiting.
13. Oversized image and seven-day reopen window.
14. Protected staff creation and authority-only ward/category/SLA configuration.

The suite includes an automated **API end-to-end test**. A separate full browser workflow also passed on 27 September: the previously submitted report SWM-2026-1B343A5B received a complaint test image; supervisor review, verification and assignment; collector acceptance, before image, start, after image and completion notes; supervisor approval; citizen confirmation and feedback. The authority dashboard then showed two reports, one closed, one active and 100% SLA compliance for the one verified resolution. These are database-backed demo results, not municipal performance claims.

The three browser-uploaded images clearly say DEMO TEST FIXTURE and are not real waste photographs. Read-only database verification confirmed CLOSED status and saved feedback. Browser validation also covers authority/citizen login, insights, form inputs and a 390×844 responsive layout. A dashboard screenshot is saved with the delivered report.

During the full browser check, a native browser confirmation dialog blocked browser automation. It was replaced with an inline confirmation group. Both Cancel action and Yes, confirm were exercised successfully. Success/duplicate-warning messages now persist across detail refreshes until dismissed; newly reported waste defaults to UNKNOWN_MIXED. The final TypeScript/Vite build and ESLint were rerun and passed after these changes.

## Warnings and corrections

The first test collection exposed a bracket typo in the new test fixture; it was corrected before running tests. Formatting/import lint findings were fixed. An empty CSS import was removed; the subsequent build completed without that warning. An attempted frontend build from the project root failed because package.json belongs under frontend; the build was rerun successfully from the correct directory. The first preview navigation happened before server startup; the running app was then opened and verified.

The final pytest run emits one upstream Starlette deprecation warning about its httpx TestClient adapter. It does not fail tests. pip-audit warns that the lockfile is not hash-locked; dependencies are fully version-pinned but artifact hashes are not included. Neither advisory scan is a guarantee of security.

## Not run

- PostgreSQL and Docker runtime: Docker unavailable on this machine.
- Real SMTP delivery: no external credentials configured; failure behavior tested with a test adapter.
- Native Android: no Android client is included; responsive web is the supported mobile interface.
- Large-dataset load tests, formal accessibility audit, independent penetration test and multi-browser/device matrix.

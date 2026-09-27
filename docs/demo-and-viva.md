# College demonstration and viva

Use the four generated demo accounts from demo-access.txt. Each role can be demonstrated in sequence by signing out and signing in. Use three distinct photographs you have permission to use: initial issue, before work and after work. The system rejects reuse of identical image content within a complaint. No synthetic evidence is seeded into the application.

The prepared database also contains a completed browser-validation report, SWM-2026-1B343A5B, with three images labelled DEMO TEST FIXTURE. These illustrate the software workflow only; they are not evidence of actual waste collection. The original SWM-DEMO-0001 report remains submitted for a fresh demonstration.

1. **Citizen:** Report waste. Choose category, waste stream and Riverside demo ward; add description and landmark. Select the map or enter coordinates. Submit, then upload a complaint photograph. Explain reference, deadline and timeline.
2. **Supervisor:** Open the report. Review, then verify the category and priority. Enter an assignment reason, inspect the recommended collector workload/score and save assignment.
3. **Waste Collector:** Open assigned job, accept, upload BEFORE photograph, start, upload a different AFTER photograph, enter notes and submit resolution.
4. **Supervisor:** Compare evidence, inspect timeline, approve. Optionally demonstrate return with reason, which requires fresh evidence.
5. **Citizen:** Inspect resolution evidence, confirm and rate. Alternatively reopen before confirming, with a reason; explain seven-day/two-reopen bounds and retained history.
6. **Government Authority:** View counts, status/ward/category/stream charts, SLA compliance, hotspot locations and CSV export. Open audit trail. The numbers derive from actual seeded and submitted records.

The demo seed contains one submitted complaint in addition to any reports you add. Operational statistics therefore change when you demonstrate the workflow. The automated test suite demonstrates overdue escalation by setting controlled test timestamps in an isolated database; do not edit production timestamps to fabricate an overdue result.

## Viva explanation

**Problem:** A citizen report alone does not ensure waste is collected. Municipal teams need ownership, deadlines, evidence and independent verification.

**Architecture:** React/TypeScript provides responsive role-specific screens. FastAPI validates requests and enforces authorization. SQLAlchemy models a central relational database with Alembic schema evolution. Local SQLite is convenient for demonstration; PostgreSQL configuration supports deployment.

**Value:** The contribution is the complete operational lifecycle: citizen evidence, ward-scoped review, workload-aware assignment, before/after evidence, supervisor approval, citizen confirmation, SLA escalation and auditability.

**Security:** Argon2 passwords, revocable HttpOnly sessions, server-side object scopes, protected staff creation, CSRF checks, image decoding/re-encoding, private storage and optimistic locking. Hiding a button alone is never considered authorization.

**Database:** Separate complaints, assignments, history, evidence, notifications, audit, configuration and feedback. Foreign keys preserve associations; unique constraints and version counters protect consistency. No operational record deletion API is exposed.

**Algorithms:** Deterministic 100/(1+workload) collector scoring after ward eligibility; Haversine duplicate warnings over seven days within 100 metres; simple geographic grid hotspots; priority-based SLA and bounded escalation levels.

**Testing:** The automated API suite executes the full lifecycle and adversarial cases, including other citizens' IDs, wrong wards, stale versions, malformed/reused images, missing evidence, reopening, migration preservation and optional email failure. Browser checks cover real sign-in, dashboard and responsive layout. Tests do not prove municipal-scale performance or external email delivery.

**Future scope:** Native Android client using the same API, official ward polygons/geocoding, SMS/cloud storage adapters, PDF reports, shared job workers, accessibility audit and larger-scale load testing. AI classification and IoT should be added only with real data/hardware and measurable benefit.

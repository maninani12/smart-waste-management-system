# Security review

Passwords use Argon2. Random 48-byte URL-safe session tokens are stored in HttpOnly, SameSite=Strict cookies; only SHA-256 digests are kept in the database. Session expiry is eight hours and logout deletes the server record. Production cookies require HTTPS via `APP_ENV=production`. Account activation is checked on every request, so deactivation immediately invalidates access.

Mutations require `X-Requested-With: swm`; foreign Origin headers and cross-site Fetch Metadata are rejected. No permissive CORS middleware is enabled. The supported frontend and API share an origin, or Vite proxies requests. Authentication/registration are limited to 15 attempts per source IP per minute inside the single application process. Reverse proxies need their own shared perimeter limits before public deployment.

Pydantic forbids extra fields. Citizen registration cannot select a role; authority controls staff creation. Citizen row scopes restrict complaints to the owner; collectors to current assignments; supervisors to their single authorized ward. Reads, uploads, evidence downloads and mutations use the same scope. Government dashboards omit citizen identity/contact fields.

Images accept only JPEG/PNG/WebP extensions and MIME types plus successful decoding. Maximum input is 5 MB and 20 million pixels. Images are resized to at most 2000×2000 and re-encoded to JPEG, removing EXIF and untrusted original filenames. Private UUID storage keys are not returned by APIs. Authenticated evidence endpoints enforce complaint scope. Image hashes are for duplicate detection and integrity comparison, not proof of authenticity.

ORM statements avoid SQL interpolation. CSV exports contain controlled reference/status/classification values and numeric IDs, not free-text citizen descriptions or private contact details. Database changes use transactions. Unique and foreign-key constraints protect associations. Version checking prevents conflicting assignments and state transitions. Evidence cycles prevent old photographs from satisfying returned or reassigned work.

Audit records cannot be changed through any API. This is application-level append-only behavior, not cryptographic tamper-proof storage: a database administrator could edit rows. Local database/evidence access is controlled by the operating system; the project is not an encrypted file vault.

Security headers prevent framing and MIME sniffing and apply a restricted content policy. API-documentation routes separately permit Swagger/ReDoc assets. Error responses do not expose database statements or passwords. Demo passwords are generated locally and excluded from Git. Production bootstrap reads passwords interactively; there are no fixed production credentials.

Before public deployment: configure HTTPS, exact allowed origins, trusted proxy behavior, shared rate limits, backup/restore checks, storage quotas, patch monitoring and operational access policies. Avoid multiple workers with the embedded scheduler. Analytics are not load-tested for municipal scale. Native mobile secure credential storage, account recovery, email verification, MFA, data retention automation and malware scanning are future extensions, not claimed controls.

Implementation references: [FastAPI response cookies](https://fastapi.tiangolo.com/advanced/response-cookies/) and [SQLAlchemy version counters](https://docs.sqlalchemy.org/en/20/orm/versioning.html).

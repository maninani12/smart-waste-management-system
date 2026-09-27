# API guide

Base prefix: `/api`. Full request schemas are generated from implementation at `/openapi.json` and displayed at `/docs`. Cookie authentication is required except health, registration and login. Send `X-Requested-With: swm` on all mutations. Browser requests must originate from an allowed origin. Eight-hour sessions are revocable; there is no JWT refresh-token flow because opaque server sessions were selected.

| Endpoint | Access and purpose |
|---|---|
| POST /auth/register | Public, creates citizen only; password >=12 characters |
| POST /auth/login; POST /auth/logout | Start/revoke session |
| GET/PATCH /auth/me | Own profile; update name only |
| GET /config | Authenticated ward/category/SLA reference data |
| POST /config/wards; POST /config/categories; PUT /config/sla | Authority configuration |
| GET/POST /users; PATCH /users/{id} | Authority staff administration; supervisors can list ward collectors |
| GET/POST /complaints | Scoped paginated list; citizen submission |
| GET /complaints/{id} | Scoped detail, history, evidence metadata and assignments |
| POST /complaints/{id}/transition | Explicit role/state transition; requires `version`, `action`, appropriate `reason` |
| GET /complaints/{id}/recommendations | Supervisor workload ranking |
| POST /complaints/{id}/assign | Supervisor: collector_id, version, reason |
| POST /complaints/{id}/evidence?stage=COMPLAINT\|BEFORE\|AFTER | Multipart `file`; stage and role constrained |
| GET /evidence/{id} | Private authenticated JPEG |
| POST /complaints/{id}/feedback | Owner, after closure; rating 1–5 and comment |
| GET /notifications; POST /notifications/{id}/read | Own notifications, latest 100 |
| GET /analytics | Supervisor ward scope or authority scope |
| GET /reports.csv | Same filters/scope as analytics; downloadable CSV |
| GET /audit?page=1 | Authority, 50 records per page |
| GET /health | Database health and demo-environment flag |

Complaint/analytics/report filters: `status`, `ward_id`, `category_id`, `waste_stream`, `priority`, `start`, `end`, `search`. Dates use YYYY-MM-DD; end date is inclusive. Complaint pagination: page >=1, limit 1–100, default 20. Newest reports appear first. Detail responses never return password hashes, session tokens, storage paths or citizen contact details.

Transitions: review, verify, reject, accept, start, submit_resolution, approve, return, confirm, reopen. Only verification accepts priority/category changes. Rejection, return, reopen, completion and assignment need reasons/notes. Workflow violations or stale versions return 409; role violations 403; invisible or absent objects 404; invalid inputs 422; unauthenticated 401; oversized images 413; login throttling 429. A conflict instructs the client to refresh before retrying.

Example submission body:

```json
{"description":"Waste accumulated near the park entrance","address":"Park entrance","latitude":17.385,"longitude":78.4867,"ward_id":1,"category_id":1,"waste_stream":"UNKNOWN_MIXED"}
```

Return values include a generated reference, a version and possible duplicate count. Evidence upload is a second step and can be retried without losing the report. In the UI the newly saved detail immediately offers image upload.

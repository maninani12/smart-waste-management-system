import asyncio
import csv
import io
import logging
import os
import secrets
import time
from collections import Counter, defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median

from fastapi import Depends, FastAPI, File, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm.exc import StaleDataError

from . import schemas as s
from .db import SessionLocal, get_db, now
from .models import (
    SLA,
    Assignment,
    Audit,
    Category,
    Complaint,
    Escalation,
    Evidence,
    Feedback,
    History,
    Notification,
    Session,
    User,
    Ward,
)
from .providers import dispatch
from .security import (
    create_session,
    current_user,
    digest,
    hasher,
    public_user,
    require,
    verify_password,
)
from .services import (
    RESOLVED,
    SLA_WARNING_HOURS,
    audit,
    check_version,
    complaint_for,
    deadline,
    duplicates,
    escalate,
    record,
    scoped,
)
from .storage import LocalStorage, clean_image

logger = logging.getLogger("swm")


async def scheduler():
    while True:
        try:
            await asyncio.to_thread(run_escalations)
        except Exception:
            logger.exception("Escalation worker failed")
        await asyncio.sleep(60)


def run_escalations():
    with SessionLocal() as db:
        count = escalate(db)
        dispatch(db)
        return count


@asynccontextmanager
async def lifespan(app):
    task = asyncio.create_task(scheduler())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Smart Waste Management API", version="1.0.0", lifespan=lifespan)
DB = Depends(get_db)
AUTH = Depends(current_user)
attempts = defaultdict(deque)
allowed_origins = set(
    os.getenv(
        "ALLOWED_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000,http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if (
            (origin and origin not in allowed_origins)
            or request.headers.get("sec-fetch-site") == "cross-site"
            or request.headers.get("x-requested-with") != "swm"
        ):
            return JSONResponse(
                {"detail": "Request origin could not be verified."}, status_code=403
            )
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https://*.tile.openstreetmap.org; connect-src 'self'; frame-src https://www.openstreetmap.org; base-uri 'self'; form-action 'self'"
    )
    if request.url.path in {"/docs", "/redoc"}:
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com; connect-src 'self'; worker-src blob:"
        )
    return response


@app.exception_handler(StaleDataError)
async def stale_handler(request, exc):
    return JSONResponse(
        {"detail": "Another user changed this record. Refresh and retry."}, status_code=409
    )


@app.exception_handler(IntegrityError)
async def integrity_handler(request, exc):
    return JSONResponse(
        {"detail": "The record already exists or conflicts with a related record."}, status_code=409
    )


def throttle(request):
    key = request.client.host
    bucket = attempts[key]
    while bucket and bucket[0] < time.monotonic() - 60:
        bucket.popleft()
    if len(bucket) >= 15:
        raise HTTPException(429, "Too many attempts. Try again in one minute.")
    bucket.append(time.monotonic())


@app.get("/api/health")
def health(db: DBSession = DB):
    db.execute(select(func.count()).select_from(Ward))
    return {"status": "ok", "demo": os.getenv("APP_ENV", "development") != "production"}


@app.post("/api/auth/register", status_code=201)
def register(data: s.Register, request: Request, db: DBSession = DB):
    throttle(request)
    u = User(
        name=data.name,
        email=str(data.email).lower(),
        password_hash=hasher.hash(data.password),
        role="CITIZEN",
    )
    db.add(u)
    db.flush()
    audit(db, u, "user.register", u.id)
    db.commit()
    return public_user(u)


@app.post("/api/auth/login")
def login(data: s.Login, request: Request, response: Response, db: DBSession = DB):
    throttle(request)
    u = db.scalar(select(User).where(User.email == str(data.email).lower()))
    valid = verify_password(u.password_hash if u else None, data.password)
    if not u or not valid or not u.active:
        raise HTTPException(401, "Invalid email or password.")
    token = create_session(db, u)
    audit(db, u, "user.login", u.id)
    db.commit()
    response.set_cookie(
        "swm_session",
        token,
        httponly=True,
        secure=os.getenv("APP_ENV") == "production",
        samesite="strict",
        max_age=28800,
        path="/",
    )
    return public_user(u)


@app.post("/api/auth/logout")
def logout(request: Request, response: Response, db: DBSession = DB):
    token = db.get(Session, digest(request.cookies.get("swm_session", "")))
    if token:
        db.delete(token)
        db.commit()
    response.delete_cookie("swm_session", path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(u: User = AUTH):
    return public_user(u)


@app.patch("/api/auth/me")
def profile(data: s.Profile, u: User = AUTH, db: DBSession = DB):
    u.name = data.name
    audit(db, u, "user.profile", u.id)
    db.commit()
    return public_user(u)


@app.get("/api/config")
def config(u: User = AUTH, db: DBSession = DB):
    return {
        "demo": os.getenv("APP_ENV", "development") != "production",
        "wards": [{"id": w.id, "name": w.name, "zone": w.zone} for w in db.scalars(select(Ward))],
        "categories": [{"id": c.id, "name": c.name} for c in db.scalars(select(Category))],
        "sla": [{"priority": r.priority, "hours": r.hours} for r in db.scalars(select(SLA))],
    }


@app.post("/api/config/wards", status_code=201)
def add_ward(data: s.WardCreate, u: User = AUTH, db: DBSession = DB):
    require(u, "GOVERNMENT_AUTHORITY")
    db.add(Ward(**data.model_dump()))
    audit(db, u, "config.ward", data.name)
    db.commit()
    return {"ok": True}


@app.post("/api/config/categories", status_code=201)
def add_category(data: s.Named, u: User = AUTH, db: DBSession = DB):
    require(u, "GOVERNMENT_AUTHORITY")
    db.add(Category(name=data.name))
    audit(db, u, "config.category", data.name)
    db.commit()
    return {"ok": True}


@app.put("/api/config/sla")
def sla(data: s.SLACreate, u: User = AUTH, db: DBSession = DB):
    require(u, "GOVERNMENT_AUTHORITY")
    rule = db.get(SLA, data.priority)
    old = rule.hours if rule else None
    db.merge(SLA(**data.model_dump()))
    audit(db, u, "config.sla", data.priority, f"{old} → {data.hours}; future deadlines only")
    db.commit()
    return {"ok": True}


@app.get("/api/users")
def users(u: User = AUTH, db: DBSession = DB):
    require(u, "GOVERNMENT_AUTHORITY", "SUPERVISOR")
    q = select(User)
    if u.role == "SUPERVISOR":
        q = q.where(User.role == "WASTE_COLLECTOR", User.ward_id == u.ward_id)
    return [public_user(x) for x in db.scalars(q)]


@app.post("/api/users", status_code=201)
def add_user(data: s.UserCreate, u: User = AUTH, db: DBSession = DB):
    require(u, "GOVERNMENT_AUTHORITY")
    if data.role in {"WASTE_COLLECTOR", "SUPERVISOR"} and not db.get(Ward, data.ward_id):
        raise HTTPException(422, "A valid ward is required for operational staff.")
    x = User(
        name=data.name,
        email=str(data.email).lower(),
        role=data.role,
        ward_id=data.ward_id,
        password_hash=hasher.hash(data.password),
    )
    db.add(x)
    db.flush()
    audit(db, u, "user.create", x.id, x.role)
    db.commit()
    return public_user(x)


@app.patch("/api/users/{uid}")
def update_user(uid: int, data: s.UserUpdate, u: User = AUTH, db: DBSession = DB):
    require(u, "GOVERNMENT_AUTHORITY")
    x = db.get(User, uid)
    if not x:
        raise HTTPException(404, "User not found.")
    if x.id == u.id and not data.active:
        raise HTTPException(422, "You cannot deactivate your own account.")
    x.active, x.available = data.active, data.available
    audit(db, u, "user.update", uid, str(data.model_dump()))
    db.commit()
    return public_user(x)


def serialized(c, db):
    fields = [
        "id",
        "reference",
        "ward_id",
        "category_id",
        "collector_id",
        "description",
        "address",
        "latitude",
        "longitude",
        "waste_stream",
        "priority",
        "status",
        "created_at",
        "deadline",
        "resolved_at",
        "closed_at",
        "version",
        "reopen_count",
        "cycle",
    ]
    result = {k: getattr(c, k) for k in fields}
    for k, v in result.items():
        if isinstance(v, datetime):
            result[k] = v.isoformat() + "Z"
    result["overdue"] = c.status not in RESOLVED and c.deadline < now()
    return result


def filtered(
    u,
    status=None,
    ward_id=None,
    category_id=None,
    waste_stream=None,
    priority=None,
    start=None,
    end=None,
    search=None,
):
    q = scoped(select(Complaint), u)
    for key, value in [
        ("status", status),
        ("ward_id", ward_id),
        ("category_id", category_id),
        ("waste_stream", waste_stream),
        ("priority", priority),
    ]:
        if value:
            q = q.where(getattr(Complaint, key) == value)
    if start:
        q = q.where(Complaint.created_at >= datetime.fromisoformat(start).replace(tzinfo=None))
    if end:
        q = q.where(
            Complaint.created_at
            < datetime.fromisoformat(end).replace(tzinfo=None) + timedelta(days=1)
        )
    if search:
        q = q.where(
            Complaint.reference.ilike(f"%{search}%") | Complaint.description.ilike(f"%{search}%")
        )
    return q


def filters(
    status: str | None = None,
    ward_id: int | None = None,
    category_id: int | None = None,
    waste_stream: s.Stream | None = None,
    priority: s.Priority | None = None,
    start: str | None = None,
    end: str | None = None,
    search: str | None = Query(None, max_length=100),
):
    try:
        for d in [start, end]:
            if d:
                datetime.strptime(d, "%Y-%m-%d")
        if start and end and start > end:
            raise ValueError()
    except ValueError:
        raise HTTPException(422, "Use a valid date range in YYYY-MM-DD format.")
    return dict(
        status=status,
        ward_id=ward_id,
        category_id=category_id,
        waste_stream=waste_stream,
        priority=priority,
        start=start,
        end=end,
        search=search,
    )


@app.get("/api/complaints")
def complaints(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    f: dict = Depends(filters),
    u: User = AUTH,
    db: DBSession = DB,
):
    q = filtered(u, **f)
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    return {
        "total": total,
        "items": [
            serialized(c, db)
            for c in db.scalars(
                q.order_by(Complaint.created_at.desc()).offset((page - 1) * limit).limit(limit)
            )
        ],
    }


@app.post("/api/complaints", status_code=201)
def create_complaint(data: s.ComplaintCreate, u: User = AUTH, db: DBSession = DB):
    require(u, "CITIZEN")
    if not db.get(Ward, data.ward_id) or not db.get(Category, data.category_id):
        raise HTTPException(422, "Choose a valid ward and category.")
    count = duplicates(db, data)
    c = Complaint(
        **data.model_dump(),
        citizen_id=u.id,
        reference=f"SWM-{now().year}-{secrets.token_hex(4).upper()}",
        deadline=deadline(db, "NORMAL"),
    )
    db.add(c)
    db.flush()
    record(db, c, u, "", "Citizen submitted complaint")
    db.commit()
    return {**serialized(c, db), "possible_duplicates": count}


@app.get("/api/complaints/{cid}")
def detail(cid: int, u: User = AUTH, db: DBSession = DB):
    c = complaint_for(db, u, cid)
    return {
        **serialized(c, db),
        "history": [
            {"status": h.status, "reason": h.reason, "created_at": h.created_at.isoformat() + "Z"}
            for h in db.scalars(
                select(History).where(History.complaint_id == cid).order_by(History.id)
            )
        ],
        "evidence": [
            {
                "id": e.id,
                "stage": e.stage,
                "cycle": e.cycle,
                "sha256": e.sha256,
                "created_at": e.created_at.isoformat() + "Z",
            }
            for e in db.scalars(select(Evidence).where(Evidence.complaint_id == cid))
        ],
        "assignments": [
            {
                "collector_id": a.collector_id,
                "reason": a.reason,
                "created_at": a.created_at.isoformat() + "Z",
            }
            for a in db.scalars(select(Assignment).where(Assignment.complaint_id == cid))
        ],
    }


@app.post("/api/complaints/{cid}/transition")
def transition(cid: int, data: s.Transition, u: User = AUTH, db: DBSession = DB):
    c = complaint_for(db, u, cid)
    check_version(c, data.version)
    rules = {
        "review": ("SUPERVISOR", {"SUBMITTED", "REOPENED"}, "UNDER_REVIEW"),
        "verify": ("SUPERVISOR", {"UNDER_REVIEW"}, "VERIFIED"),
        "reject": ("SUPERVISOR", {"SUBMITTED", "UNDER_REVIEW"}, "REJECTED"),
        "accept": ("WASTE_COLLECTOR", {"ASSIGNED"}, "ACCEPTED"),
        "start": ("WASTE_COLLECTOR", {"ACCEPTED"}, "IN_PROGRESS"),
        "submit_resolution": ("WASTE_COLLECTOR", {"IN_PROGRESS"}, "RESOLUTION_SUBMITTED"),
        "approve": ("SUPERVISOR", {"RESOLUTION_SUBMITTED"}, "RESOLUTION_VERIFIED"),
        "return": ("SUPERVISOR", {"RESOLUTION_SUBMITTED"}, "IN_PROGRESS"),
        "confirm": ("CITIZEN", {"RESOLUTION_VERIFIED"}, "CLOSED"),
        "reopen": ("CITIZEN", {"RESOLUTION_VERIFIED"}, "REOPENED"),
    }
    role, sources, destination = rules[data.action]
    require(u, role)
    if c.status not in sources:
        raise HTTPException(409, "This transition is not allowed from the current state.")
    if data.action in {"reject", "return", "reopen", "submit_resolution"} and len(data.reason) < 3:
        raise HTTPException(422, "A meaningful reason or completion note is required.")
    if (data.priority or data.category_id) and data.action != "verify":
        raise HTTPException(422, "Classification changes are only allowed during verification.")
    if data.action == "verify":
        previous_classification = f"{c.category_id}/{c.priority}"
        if data.category_id:
            if not db.get(Category, data.category_id):
                raise HTTPException(422, "Invalid category.")
            c.category_id = data.category_id
        c.priority = data.priority or c.priority
        # Initial SLA starts on submission, not on delayed verification.
        c.deadline = (
            c.created_at + timedelta(hours=db.get(SLA, c.priority).hours)
            if c.reopen_count == 0
            else deadline(db, c.priority)
        )
        audit(
            db,
            u,
            "complaint.classification",
            cid,
            f"{previous_classification} → {c.category_id}/{c.priority}",
        )
    if data.action in {"start", "submit_resolution"}:
        stages = set(
            db.scalars(
                select(Evidence.stage).where(
                    Evidence.complaint_id == cid, Evidence.cycle == c.cycle
                )
            )
        )
        needed = {"BEFORE"} if data.action == "start" else {"BEFORE", "AFTER"}
        if not needed.issubset(stages):
            raise HTTPException(422, f"Upload required evidence: {', '.join(sorted(needed))}.")
    if data.action == "approve":
        c.resolved_at = now()
    if data.action == "return":
        # Returned work needs fresh evidence; earlier evidence stays in the timeline.
        c.cycle += 1
    if data.action == "confirm":
        c.closed_at = now()
    if data.action == "reopen":
        if c.reopen_count >= 2 or not c.resolved_at or now() > c.resolved_at + timedelta(days=7):
            raise HTTPException(422, "Reopening is allowed within 7 days, for up to two cycles.")
        c.reopen_count += 1
        c.cycle += 1
        c.collector_id = None
        c.resolved_at = None
        c.deadline = deadline(db, c.priority)
    previous = c.status
    c.status = destination
    record(db, c, u, previous, data.reason)
    db.commit()
    return serialized(c, db)


@app.get("/api/complaints/{cid}/recommendations")
def recommendations(cid: int, u: User = AUTH, db: DBSession = DB):
    require(u, "SUPERVISOR")
    c = complaint_for(db, u, cid)
    people = db.scalars(
        select(User).where(
            User.role == "WASTE_COLLECTOR",
            User.ward_id == c.ward_id,
            User.active.is_(True),
            User.available.is_(True),
        )
    )
    results = []
    for p in people:
        workload = db.scalar(
            select(func.count())
            .select_from(Complaint)
            .where(Complaint.collector_id == p.id, Complaint.status.not_in(RESOLVED))
        )
        results.append(
            {
                "id": p.id,
                "name": p.name,
                "workload": workload,
                "score": round(100 / (1 + workload), 2),
                "reason": "Active, available, same ward; ranked by active workload.",
            }
        )
    return sorted(results, key=lambda x: (-x["score"], x["id"]))


@app.post("/api/complaints/{cid}/assign")
def assign(cid: int, data: s.Assign, u: User = AUTH, db: DBSession = DB):
    require(u, "SUPERVISOR")
    c = complaint_for(db, u, cid)
    check_version(c, data.version)
    if c.status not in {"VERIFIED", "ASSIGNED", "ACCEPTED", "IN_PROGRESS"}:
        raise HTTPException(
            409,
            "Verify the complaint before assigning; submitted resolutions must be reviewed first.",
        )
    collector = db.get(User, data.collector_id)
    if (
        not collector
        or collector.role != "WASTE_COLLECTOR"
        or collector.ward_id != c.ward_id
        or not collector.active
        or not collector.available
    ):
        raise HTTPException(422, "Collector must be active, available and assigned to this ward.")
    if c.collector_id == collector.id:
        raise HTTPException(422, "This collector is already assigned.")
    old = c.collector_id
    if old:
        c.cycle += 1
    c.collector_id = collector.id
    previous, c.status = c.status, "ASSIGNED"
    db.add(
        Assignment(
            complaint_id=cid, collector_id=collector.id, supervisor_id=u.id, reason=data.reason
        )
    )
    if old:
        db.add(
            Notification(
                user_id=old, complaint_id=cid, message=f"{c.reference}: assignment transferred"
            )
        )
    record(db, c, u, previous, f"Collector {old} → {collector.id}. {data.reason}")
    db.commit()
    return serialized(c, db)


@app.post("/api/complaints/{cid}/evidence", status_code=201)
async def upload(
    cid: int, stage: str, file: UploadFile = File(...), u: User = AUTH, db: DBSession = DB
):
    c = complaint_for(db, u, cid)
    allowed = (
        u.role == "CITIZEN" and stage == "COMPLAINT" and c.status in {"SUBMITTED", "UNDER_REVIEW"}
    ) or (
        u.role == "WASTE_COLLECTOR"
        and (
            (stage == "BEFORE" and c.status in {"ACCEPTED", "IN_PROGRESS"})
            or (stage == "AFTER" and c.status == "IN_PROGRESS")
        )
    )
    if not allowed:
        raise HTTPException(403, "Evidence cannot be uploaded at this stage by your role.")
    if (
        db.scalar(
            select(func.count())
            .select_from(Evidence)
            .where(Evidence.complaint_id == cid, Evidence.cycle == c.cycle)
        )
        >= 12
    ):
        raise HTTPException(422, "Maximum 12 images per work cycle.")
    raw = await file.read(5 * 1024 * 1024 + 1)
    content, checksum = clean_image(raw, file.filename, file.content_type)
    reused = db.scalar(
        select(Evidence).where(Evidence.complaint_id == cid, Evidence.sha256 == checksum)
    )
    if reused:
        raise HTTPException(
            422, "This image was already used for this complaint. Upload fresh evidence."
        )
    storage = LocalStorage()
    key = storage.save(content)
    e = Evidence(
        complaint_id=cid,
        uploader_id=u.id,
        stage=stage,
        cycle=c.cycle,
        storage_key=key,
        sha256=checksum,
        size=len(content),
    )
    db.add(e)
    # Update version so concurrent reassignment cannot attach evidence to a stale cycle.
    c.version += 1
    audit(db, u, "evidence.upload", cid, f"{stage}; sha256={checksum}")
    try:
        db.commit()
    except Exception:
        storage.path(key).unlink(missing_ok=True)
        raise
    return {"id": e.id, "stage": stage}


@app.get("/api/evidence/{eid}")
def evidence(eid: int, u: User = AUTH, db: DBSession = DB):
    e = db.get(Evidence, eid)
    if not e:
        raise HTTPException(404, "Evidence not found.")
    complaint_for(db, u, e.complaint_id)
    path = LocalStorage().path(e.storage_key)
    if not path.is_file():
        raise HTTPException(404, "Evidence file unavailable.")
    return FileResponse(path, media_type="image/jpeg")


@app.post("/api/complaints/{cid}/feedback")
def feedback(cid: int, data: s.FeedbackCreate, u: User = AUTH, db: DBSession = DB):
    require(u, "CITIZEN")
    c = complaint_for(db, u, cid)
    if c.status != "CLOSED":
        raise HTTPException(409, "Confirm resolution before leaving feedback.")
    db.add(Feedback(complaint_id=cid, **data.model_dump()))
    audit(db, u, "complaint.feedback", cid, str(data.rating))
    db.commit()
    return {"ok": True}


@app.get("/api/notifications")
def notifications(u: User = AUTH, db: DBSession = DB):
    return [
        {
            "id": n.id,
            "complaint_id": n.complaint_id,
            "message": n.message,
            "read": n.read,
            "created_at": n.created_at.isoformat() + "Z",
        }
        for n in db.scalars(
            select(Notification)
            .where(Notification.user_id == u.id)
            .order_by(Notification.id.desc())
            .limit(100)
        )
    ]


@app.post("/api/notifications/{nid}/read")
def read_notification(nid: int, u: User = AUTH, db: DBSession = DB):
    n = db.get(Notification, nid)
    if not n or n.user_id != u.id:
        raise HTTPException(404, "Notification not found.")
    n.read = True
    db.commit()
    return {"ok": True}


@app.get("/api/analytics")
def analytics(f: dict = Depends(filters), u: User = AUTH, db: DBSession = DB):
    require(u, "SUPERVISOR", "GOVERNMENT_AUTHORITY")
    rows = list(db.scalars(filtered(u, **f)))
    resolved = [c for c in rows if c.resolved_at]
    durations = [(c.resolved_at - c.created_at).total_seconds() / 3600 for c in resolved]
    hotspots = Counter((round(c.latitude, 3), round(c.longitude, 3)) for c in rows)
    return {
        "total": len(rows),
        "open": sum(c.status not in RESOLVED for c in rows),
        "closed": sum(c.status == "CLOSED" for c in rows),
        "overdue": sum(c.status not in RESOLVED and c.deadline < now() for c in rows),
        "approaching": sum(
            c.status not in RESOLVED
            and now() <= c.deadline <= now() + timedelta(hours=SLA_WARNING_HOURS)
            for c in rows
        ),
        "reopened": sum(c.reopen_count > 0 for c in rows),
        "sla_compliance": round(
            100 * sum(c.resolved_at <= c.deadline for c in resolved) / len(resolved), 1
        )
        if resolved
        else None,
        "average_resolution_hours": round(mean(durations), 1) if durations else None,
        "median_resolution_hours": round(median(durations), 1) if durations else None,
        "status": dict(Counter(c.status for c in rows)),
        "wards": dict(Counter(str(c.ward_id) for c in rows)),
        "categories": dict(Counter(str(c.category_id) for c in rows)),
        "streams": dict(Counter(c.waste_stream for c in rows)),
        "priorities": dict(Counter(c.priority for c in rows)),
        "trend": dict(sorted(Counter(c.created_at.strftime("%Y-%m-%d") for c in rows).items())),
        "hotspots": [
            {
                "latitude": p[0],
                "longitude": p[1],
                "count": n,
                "open": sum(
                    round(c.latitude, 3) == p[0]
                    and round(c.longitude, 3) == p[1]
                    and c.status not in RESOLVED
                    for c in rows
                ),
            }
            for p, n in hotspots.most_common(50)
        ],
        "collectors": [
            {
                "collector_id": uid,
                "assigned": sum(c.collector_id == uid for c in rows),
                "resolved": sum(c.collector_id == uid and c.resolved_at is not None for c in rows),
            }
            for uid in sorted({c.collector_id for c in rows if c.collector_id})
        ],
        "escalated": len(
            set(
                db.scalars(
                    select(Escalation.complaint_id).where(
                        Escalation.level > 0, Escalation.complaint_id.in_([c.id for c in rows])
                    )
                )
            )
        ),
    }


@app.get("/api/reports.csv")
def report(f: dict = Depends(filters), u: User = AUTH, db: DBSession = DB):
    require(u, "SUPERVISOR", "GOVERNMENT_AUTHORITY")
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Smart Waste operational report",
            "Generated UTC",
            now().isoformat(),
            "DEMO" if os.getenv("APP_ENV", "development") != "production" else "Municipal data",
        ]
    )
    writer.writerow(["Filters", str({k: v for k, v in f.items() if v})])
    writer.writerow(
        [
            "Reference",
            "Status",
            "Ward",
            "Category",
            "Waste stream",
            "Priority",
            "Created UTC",
            "Deadline UTC",
        ]
    )
    for c in db.scalars(filtered(u, **f)):
        writer.writerow(
            [
                c.reference,
                c.status,
                c.ward_id,
                c.category_id,
                c.waste_stream,
                c.priority,
                c.created_at.isoformat(),
                c.deadline.isoformat(),
            ]
        )
    return Response(
        output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="waste-report.csv"'},
    )


@app.get("/api/audit")
def audit_list(page: int = Query(1, ge=1), u: User = AUTH, db: DBSession = DB):
    require(u, "GOVERNMENT_AUTHORITY")
    return [
        {
            "id": a.id,
            "action": a.action,
            "entity": a.entity,
            "detail": a.detail,
            "created_at": a.created_at.isoformat() + "Z",
        }
        for a in db.scalars(
            select(Audit).order_by(Audit.id.desc()).offset((page - 1) * 50).limit(50)
        )
    ]


if Path("frontend/dist").is_dir():
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="web")

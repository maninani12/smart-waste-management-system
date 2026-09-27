import math
import os
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select

from .db import now
from .models import SLA, Audit, Complaint, Delivery, Escalation, History, Notification, User

TERMINAL = {"CLOSED", "REJECTED"}
RESOLVED = TERMINAL | {"RESOLUTION_VERIFIED"}
SLA_WARNING_HOURS = float(os.getenv("SLA_WARNING_HOURS", "2"))
ESCALATE_AFTER_HOURS = float(os.getenv("ESCALATE_AFTER_HOURS", "24"))


def scoped(query, user):
    if user.role == "CITIZEN":
        return query.where(Complaint.citizen_id == user.id)
    if user.role == "WASTE_COLLECTOR":
        return query.where(Complaint.collector_id == user.id)
    if user.role == "SUPERVISOR":
        return query.where(Complaint.ward_id == user.ward_id)
    return query


def complaint_for(db, user, cid):
    c = db.scalar(scoped(select(Complaint).where(Complaint.id == cid), user))
    if not c:
        raise HTTPException(404, "Complaint not found.")
    return c


def check_version(c, version):
    if c.version != version:
        raise HTTPException(409, "This complaint changed. Refresh before trying again.")


def audit(db, actor, action, entity, detail=""):
    db.add(
        Audit(
            actor_id=actor.id if actor else None, action=action, entity=str(entity), detail=detail
        )
    )


def notify(db, c, message, recipients=None):
    if recipients is None:
        recipients = {c.citizen_id, c.collector_id}
        recipients.update(
            db.scalars(
                select(User.id).where(
                    User.role == "SUPERVISOR", User.ward_id == c.ward_id, User.active.is_(True)
                )
            )
        )
    for uid in set(recipients) - {None}:
        notice = Notification(user_id=uid, complaint_id=c.id, message=f"{c.reference}: {message}")
        db.add(notice)
        db.flush()
        db.add(Delivery(notification_id=notice.id))


def record(db, c, user, previous, reason=""):
    db.add(
        History(
            complaint_id=c.id, actor_id=user.id, previous=previous, status=c.status, reason=reason
        )
    )
    audit(db, user, "complaint.transition", c.id, f"{previous} → {c.status}; {reason}")
    notify(db, c, c.status.replace("_", " ").lower())


def deadline(db, priority):
    rule = db.get(SLA, priority)
    if not rule:
        raise HTTPException(503, "SLA configuration is missing. Run setup.")
    return now() + timedelta(hours=rule.hours)


def distance(a, b, x, y):
    p, q = math.radians(a), math.radians(x)
    h = (
        math.sin((q - p) / 2) ** 2
        + math.cos(p) * math.cos(q) * math.sin(math.radians(y - b) / 2) ** 2
    )
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


def duplicates(db, data):
    candidates = db.scalars(
        select(Complaint).where(
            Complaint.category_id == data.category_id,
            Complaint.created_at > now() - timedelta(days=7),
            Complaint.status.not_in(RESOLVED),
        )
    )
    return sum(
        distance(data.latitude, data.longitude, c.latitude, c.longitude) <= 100 for c in candidates
    )


def escalate(db):
    count = 0
    for c in db.scalars(
        select(Complaint).where(
            Complaint.deadline < now() + timedelta(hours=SLA_WARNING_HOURS),
            Complaint.status.not_in(RESOLVED),
        )
    ):
        level = (
            2
            if now() > c.deadline + timedelta(hours=ESCALATE_AFTER_HOURS)
            else 1
            if now() > c.deadline
            else 0
        )
        exists = db.scalar(
            select(Escalation).where(
                Escalation.complaint_id == c.id,
                Escalation.cycle == c.cycle,
                Escalation.level == level,
            )
        )
        if exists:
            continue
        db.add(Escalation(complaint_id=c.id, cycle=c.cycle, level=level))
        role = "GOVERNMENT_AUTHORITY" if level == 2 else "SUPERVISOR"
        q = select(User.id).where(User.role == role, User.active.is_(True))
        if level < 2:
            q = q.where(User.ward_id == c.ward_id)
        notify(
            db,
            c,
            "SLA approaching deadline" if level == 0 else f"SLA escalation level {level}",
            db.scalars(q),
        )
        audit(db, None, "sla.escalation", c.id, f"cycle={c.cycle}, level={level}")
        count += 1
    db.commit()
    return count

"""Idempotent, development-only seed; random credentials are stored locally."""

import os
import secrets
from pathlib import Path

from sqlalchemy import select

from .db import SessionLocal
from .models import SLA, Category, Complaint, User, Ward
from .security import hasher
from .services import deadline, record


def seed():
    if os.getenv("APP_ENV") == "production":
        raise RuntimeError("Demo seed is disabled in production.")
    credentials = []
    with SessionLocal() as db:
        for name, zone in [
            ("Riverside · Demo Ward", "North · Demo Zone"),
            ("Garden District · Demo Ward", "South · Demo Zone"),
        ]:
            if not db.scalar(select(Ward).where(Ward.name == name)):
                db.add(Ward(name=name, zone=zone))
        for name in [
            "Garbage accumulation",
            "Overflowing bin",
            "Missed collection",
            "Illegal dumping",
            "Waste burning",
            "Roadside waste",
            "Other",
        ]:
            if not db.scalar(select(Category).where(Category.name == name)):
                db.add(Category(name=name))
        for p, hours in [("LOW", 120), ("NORMAL", 72), ("HIGH", 24), ("URGENT", 8)]:
            if not db.get(SLA, p):
                db.add(SLA(priority=p, hours=hours))
        db.flush()
        ward = db.scalar(select(Ward).order_by(Ward.id))
        for name, role, address in [
            ("Aarav · Demo Citizen", "CITIZEN", "citizen"),
            ("Meera · Demo Collector", "WASTE_COLLECTOR", "collector"),
            ("Ravi · Demo Supervisor", "SUPERVISOR", "supervisor"),
            ("Ananya · Demo Authority", "GOVERNMENT_AUTHORITY", "authority"),
        ]:
            email = f"{address}@demo.example"
            if not db.scalar(select(User).where(User.email == email)):
                password = secrets.token_urlsafe(16)
                db.add(
                    User(
                        name=name,
                        email=email,
                        role=role,
                        ward_id=ward.id if role in {"SUPERVISOR", "WASTE_COLLECTOR"} else None,
                        password_hash=hasher.hash(password),
                    )
                )
                credentials.append(f"{role}\nEmail: {email}\nPassword: {password}\n")
        db.flush()
        citizen = db.scalar(select(User).where(User.email == "citizen@demo.example"))
        if not db.scalar(select(Complaint).where(Complaint.reference == "SWM-DEMO-0001")):
            category = db.scalar(select(Category).order_by(Category.id))
            c = Complaint(
                reference="SWM-DEMO-0001",
                citizen_id=citizen.id,
                ward_id=ward.id,
                category_id=category.id,
                description="DEMO: Waste has accumulated beside the community park entrance. Please arrange collection.",
                address="Community park entrance · illustrative demo location",
                latitude=17.385,
                longitude=78.4867,
                waste_stream="UNKNOWN_MIXED",
                deadline=deadline(db, "NORMAL"),
            )
            db.add(c)
            db.flush()
            record(db, c, citizen, "", "Clearly labelled demo seed record")
        db.commit()
    if credentials:
        with Path("demo-access.txt").open("a", encoding="utf-8") as f:
            f.write(
                "LOCAL DEVELOPMENT ACCOUNTS — never use in production\n\n" + "\n".join(credentials)
            )
    print("Demo setup ready. Credentials are in demo-access.txt (not printed or committed).")


if __name__ == "__main__":
    seed()

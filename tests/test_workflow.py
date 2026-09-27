import io
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from backend.db import Base, get_db, now
from backend.main import app, attempts
from backend.models import SLA, Audit, Category, Complaint, Escalation, Notification, User, Ward
from backend.security import hasher
from backend.services import distance, escalate

PASSWORD = "Test-only-password-123!"


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "evidence"))
    attempts.clear()
    with factory() as db:
        db.add_all(
            [
                Ward(id=1, name="A", zone="North"),
                Ward(id=2, name="B", zone="South"),
                Category(id=1, name="Garbage"),
            ]
        )
        db.add_all(
            [
                SLA(priority=p, hours=h)
                for p, h in [("NORMAL", 72), ("HIGH", 24), ("LOW", 120), ("URGENT", 8)]
            ]
        )
        db.flush()
        for index, (key, role, ward) in enumerate(
            [
                ("citizen", "CITIZEN", None),
                ("other", "CITIZEN", None),
                ("collector", "WASTE_COLLECTOR", 1),
                ("supervisor", "SUPERVISOR", 1),
                ("authority", "GOVERNMENT_AUTHORITY", None),
                ("outsider", "SUPERVISOR", 2),
                ("farcollector", "WASTE_COLLECTOR", 2),
            ],
            1,
        ):
            db.add(
                User(
                    id=index,
                    name=key,
                    email=f"{key}@example.com",
                    role=role,
                    ward_id=ward,
                    password_hash=hasher.hash(PASSWORD),
                )
            )
        db.commit()

    def override():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    clients = {}
    for key in [
        "citizen",
        "other",
        "collector",
        "supervisor",
        "authority",
        "outsider",
        "farcollector",
    ]:
        client = TestClient(app, headers={"X-Requested-With": "swm"})
        assert (
            client.post(
                "/api/auth/login", json={"email": f"{key}@example.com", "password": PASSWORD}
            ).status_code
            == 200
        )
        clients[key] = client
    yield clients, factory
    for client in clients.values():
        client.close()
    app.dependency_overrides.clear()
    engine.dispose()


def create(clients, **kwargs):
    payload = dict(
        description="Waste accumulated near the park",
        address="Park entrance",
        latitude=17.385,
        longitude=78.4867,
        ward_id=1,
        category_id=1,
        waste_stream="WET",
    )
    payload.update(kwargs)
    r = clients["citizen"].post("/api/complaints", json=payload)
    assert r.status_code == 201, r.text
    return r.json()


def action(clients, who, c, name, **kwargs):
    r = clients[who].post(
        f"/api/complaints/{c['id']}/transition",
        json={"action": name, "version": c["version"], **kwargs},
    )
    assert r.status_code == 200, r.text
    return r.json()


def picture(color):
    b = io.BytesIO()
    Image.new("RGB", (32, 32), color).save(b, format="PNG")
    return b.getvalue()


def upload(clients, who, c, stage, color):
    r = clients[who].post(
        f"/api/complaints/{c['id']}/evidence?stage={stage}",
        files={"file": ("photo.png", picture(color), "image/png")},
    )
    assert r.status_code == 201, r.text
    return clients[who].get(f"/api/complaints/{c['id']}").json()


def assign(clients, c):
    r = clients["supervisor"].post(
        f"/api/complaints/{c['id']}/assign",
        json={"collector_id": 3, "version": c["version"], "reason": "Lowest workload in ward"},
    )
    assert r.status_code == 200, r.text
    return r.json()


def resolved(clients):
    c = create(clients)
    c = upload(clients, "citizen", c, "COMPLAINT", "red")
    c = action(clients, "supervisor", c, "review")
    c = action(clients, "supervisor", c, "verify", priority="HIGH")
    c = assign(clients, c)
    c = action(clients, "collector", c, "accept")
    c = upload(clients, "collector", c, "BEFORE", "green")
    c = action(clients, "collector", c, "start")
    c = upload(clients, "collector", c, "AFTER", "blue")
    c = action(
        clients,
        "collector",
        c,
        "submit_resolution",
        reason="Site cleared and segregated waste collected",
    )
    return action(clients, "supervisor", c, "approve")


def test_complete_workflow_and_analytics(env):
    clients, factory = env
    c = resolved(clients)
    c = action(clients, "citizen", c, "confirm")
    assert c["status"] == "CLOSED"
    r = clients["citizen"].post(
        f"/api/complaints/{c['id']}/feedback", json={"rating": 5, "comment": "Clean site"}
    )
    assert r.status_code == 200
    a = clients["authority"].get("/api/analytics").json()
    assert a["closed"] == a["total"] == 1
    assert a["sla_compliance"] == 100
    detail = clients["citizen"].get(f"/api/complaints/{c['id']}").json()
    assert len(detail["history"]) == 9
    assert len(detail["evidence"]) == 3
    assert "citizen_id" not in detail
    with factory() as db:
        assert len(list(db.scalars(select(Audit)))) >= 12
        assert len(list(db.scalars(select(Notification)))) >= 10


def test_object_authorization_and_roles(env):
    clients, _ = env
    c = create(clients)
    for key in ["other", "collector", "outsider", "farcollector"]:
        assert clients[key].get(f"/api/complaints/{c['id']}").status_code == 404
        assert clients[key].get("/api/complaints").json()["total"] == 0
    assert clients["citizen"].get("/api/analytics").status_code == 403
    assert clients["collector"].get("/api/reports.csv").status_code == 403
    assert clients["supervisor"].get("/api/audit").status_code == 403
    r = clients["citizen"].post(
        f"/api/complaints/{c['id']}/transition", json={"action": "review", "version": c["version"]}
    )
    assert r.status_code == 403


def test_auth_registration_logout_csrf(env):
    clients, _ = env
    anonymous = TestClient(app, headers={"X-Requested-With": "swm"})
    assert anonymous.get("/api/complaints").status_code == 401
    assert (
        anonymous.post(
            "/api/auth/login", json={"email": "citizen@example.com", "password": "wrong"}
        ).status_code
        == 401
    )
    payload = {"name": "New Citizen", "email": "new@example.com", "password": PASSWORD}
    assert (
        anonymous.post(
            "/api/auth/register", json={**payload, "role": "GOVERNMENT_AUTHORITY"}
        ).status_code
        == 422
    )
    assert anonymous.post("/api/auth/register", json=payload).status_code == 201
    assert anonymous.post("/api/auth/register", json=payload).status_code == 409
    assert (
        anonymous.post(
            "/api/auth/login", json={"email": payload["email"], "password": PASSWORD}
        ).json()["role"]
        == "CITIZEN"
    )
    r = anonymous.post("/api/auth/logout", headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    assert anonymous.post("/api/auth/logout").status_code == 200
    assert anonymous.get("/api/auth/me").status_code == 401
    assert TestClient(app).post("/api/auth/logout").status_code == 403


def test_invalid_transition_evidence_and_concurrency(env):
    clients, _ = env
    c = create(clients)
    assert (
        clients["supervisor"]
        .post(
            f"/api/complaints/{c['id']}/transition",
            json={"action": "approve", "version": c["version"]},
        )
        .status_code
        == 409
    )
    new = action(clients, "supervisor", c, "review")
    assert (
        clients["supervisor"]
        .post(
            f"/api/complaints/{c['id']}/transition",
            json={"action": "verify", "version": c["version"]},
        )
        .status_code
        == 409
    )
    c = action(clients, "supervisor", new, "verify")
    assert (
        clients["supervisor"]
        .post(
            f"/api/complaints/{c['id']}/assign",
            json={"collector_id": 7, "version": c["version"], "reason": "Wrong ward"},
        )
        .status_code
        == 422
    )
    c = assign(clients, c)
    c = action(clients, "collector", c, "accept")
    assert (
        clients["collector"]
        .post(
            f"/api/complaints/{c['id']}/transition",
            json={"action": "start", "version": c["version"]},
        )
        .status_code
        == 422
    )
    assert (
        clients["collector"]
        .post(
            f"/api/complaints/{c['id']}/evidence?stage=BEFORE",
            files={"file": ("fake.png", b"not an image", "image/png")},
        )
        .status_code
        == 422
    )
    assert (
        clients["collector"]
        .post(
            f"/api/complaints/{c['id']}/evidence?stage=BEFORE",
            files={"file": ("attack.exe", picture("red"), "image/png")},
        )
        .status_code
        == 422
    )
    c = upload(clients, "collector", c, "BEFORE", "red")
    c = action(clients, "collector", c, "start")
    assert (
        clients["collector"]
        .post(
            f"/api/complaints/{c['id']}/evidence?stage=AFTER",
            files={"file": ("same.png", picture("red"), "image/png")},
        )
        .status_code
        == 422
    )
    eid = clients["collector"].get(f"/api/complaints/{c['id']}").json()["evidence"][0]["id"]
    assert clients["other"].get(f"/api/evidence/{eid}").status_code == 404
    assert clients["citizen"].get(f"/api/evidence/{eid}").status_code == 200


def test_reopen_and_fresh_work_cycle(env):
    clients, _ = env
    c = resolved(clients)
    assert (
        clients["citizen"]
        .post(
            f"/api/complaints/{c['id']}/transition",
            json={"action": "reopen", "version": c["version"], "reason": ""},
        )
        .status_code
        == 422
    )
    c = action(clients, "citizen", c, "reopen", reason="Waste remains behind the entrance")
    assert c["cycle"] == 1 and c["reopen_count"] == 1 and c["collector_id"] is None
    c = action(clients, "supervisor", c, "review")
    c = action(clients, "supervisor", c, "verify")
    c = assign(clients, c)
    c = action(clients, "collector", c, "accept")
    assert (
        clients["collector"]
        .post(
            f"/api/complaints/{c['id']}/transition",
            json={"action": "start", "version": c["version"]},
        )
        .status_code
        == 422
    )


def test_sla_escalation_idempotence_duplicate_and_filters(env):
    clients, factory = env
    c = create(clients)
    assert create(clients)["possible_duplicates"] == 1
    assert distance(0, 0, 0, 1) == pytest.approx(111195, rel=0.001)
    with factory() as db:
        row = db.get(Complaint, c["id"])
        row.deadline = now() - timedelta(hours=1)
        db.commit()
        assert escalate(db) == 1
        assert escalate(db) == 0
        row.deadline = now() - timedelta(hours=25)
        db.commit()
        assert escalate(db) == 1
        assert len(list(db.scalars(select(Escalation)))) == 2
    a = clients["authority"].get("/api/analytics").json()
    assert a["overdue"] == 1 and a["escalated"] == 1
    assert clients["authority"].get("/api/analytics?ward_id=2").json()["total"] == 0
    assert clients["authority"].get("/api/analytics?start=invalid").status_code == 422
    assert (
        clients["authority"].get("/api/analytics?start=2026-10-01&end=2026-01-01").status_code
        == 422
    )
    r = clients["authority"].get("/api/reports.csv?status=SUBMITTED")
    assert r.status_code == 200 and c["reference"] in r.text
    assert "citizen@example.com" not in r.text


def test_validation_notifications_and_account_control(env):
    clients, _ = env
    assert clients["citizen"].post("/api/complaints", json={"latitude": 200}).status_code == 422
    c = create(clients)
    n = clients["citizen"].get("/api/notifications").json()[0]
    assert clients["other"].post(f"/api/notifications/{n['id']}/read").status_code == 404
    assert clients["citizen"].post(f"/api/notifications/{n['id']}/read").status_code == 200
    assert clients["authority"].patch("/api/users/1", json={"active": False}).status_code == 200
    assert clients["citizen"].get(f"/api/complaints/{c['id']}").status_code == 401
    assert clients["authority"].patch("/api/users/5", json={"active": False}).status_code == 422


def test_assignment_recommendation_and_reassignment(env):
    clients, factory = env
    c = create(clients)
    c = action(clients, "supervisor", c, "review")
    c = action(clients, "supervisor", c, "verify")
    rec = clients["supervisor"].get(f"/api/complaints/{c['id']}/recommendations").json()
    assert rec[0]["id"] == 3 and rec[0]["score"] == 100
    c = assign(clients, c)
    with factory() as db:
        db.add(
            User(
                id=8,
                name="Second collector",
                email="second@example.com",
                role="WASTE_COLLECTOR",
                ward_id=1,
                password_hash=hasher.hash(PASSWORD),
            )
        )
        db.commit()
    rec = clients["supervisor"].get(f"/api/complaints/{c['id']}/recommendations").json()
    assert rec[0]["id"] == 8 and rec[1]["score"] == 50
    r = clients["supervisor"].post(
        f"/api/complaints/{c['id']}/assign",
        json={"collector_id": 8, "version": c["version"], "reason": "Cover unavailable shift"},
    )
    assert r.status_code == 200 and r.json()["cycle"] == 1
    assert clients["collector"].get(f"/api/complaints/{c['id']}").status_code == 404


def test_email_adapter_failure_does_not_rollback_workflow(env, monkeypatch):
    from backend import providers
    from backend.models import Delivery

    clients, factory = env
    c = create(clients)
    with factory() as db:
        monkeypatch.setattr(providers, "email_provider", lambda: None)
        providers.dispatch(db)
        assert all(d.status == "NOT_CONFIGURED" for d in db.scalars(select(Delivery)))
        assert db.get(Complaint, c["id"]).status == "SUBMITTED"
    action(clients, "supervisor", c, "review")

    class FailingProvider:
        def send(self, recipient, message):
            raise OSError("Offline")

    monkeypatch.setattr(providers, "email_provider", lambda: FailingProvider())
    with factory() as db:
        providers.dispatch(db)
        retried = list(db.scalars(select(Delivery).where(Delivery.status == "RETRY")))
        assert retried and all(d.attempts == 1 for d in retried)
        assert db.get(Complaint, c["id"]).status == "UNDER_REVIEW"


def test_returned_work_needs_fresh_evidence(env):
    clients, _ = env
    c = create(clients)
    c = action(clients, "supervisor", c, "review")
    c = action(clients, "supervisor", c, "verify")
    c = assign(clients, c)
    c = action(clients, "collector", c, "accept")
    c = upload(clients, "collector", c, "BEFORE", "red")
    c = action(clients, "collector", c, "start")
    c = upload(clients, "collector", c, "AFTER", "blue")
    c = action(clients, "collector", c, "submit_resolution", reason="Work complete")
    c = action(clients, "supervisor", c, "return", reason="Additional cleanup required")
    r = clients["collector"].post(
        f"/api/complaints/{c['id']}/transition",
        json={
            "action": "submit_resolution",
            "version": c["version"],
            "reason": "Resubmitting old images",
        },
    )
    assert r.status_code == 422


def test_migrations_on_empty_database_and_preserve_data(tmp_path):
    import os
    import subprocess
    import sys

    from sqlalchemy import inspect, text

    url = f"sqlite:///{tmp_path / 'migrations.db'}"
    environment = {**os.environ, "DATABASE_URL": url}
    first = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "001"],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert first.returncode == 0, first.stderr
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(text("INSERT INTO wards (name,zone) VALUES ('Preserved','North')"))
    second = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert second.returncode == 0, second.stderr
    assert "notification_deliveries" in inspect(engine).get_table_names()
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT name FROM wards")) == "Preserved"
    again = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=environment,
        capture_output=True,
        text=True,
    )
    assert again.returncode == 0, again.stderr
    engine.dispose()


def test_auth_rate_limit_and_expired_session(env):
    from backend.models import Session

    clients, factory = env
    with factory() as db:
        session = db.scalar(select(Session).where(Session.user_id == 1))
        session.expires_at = now() - timedelta(seconds=1)
        db.commit()
    assert clients["citizen"].get("/api/auth/me").status_code == 401
    attempts.clear()
    anonymous = TestClient(app, headers={"X-Requested-With": "swm"})
    for _ in range(15):
        assert (
            anonymous.post(
                "/api/auth/login", json={"email": "unknown@example.com", "password": "wrong"}
            ).status_code
            == 401
        )
    assert (
        anonymous.post(
            "/api/auth/login", json={"email": "unknown@example.com", "password": "wrong"}
        ).status_code
        == 429
    )


def test_upload_size_and_reopen_window(env):
    clients, factory = env
    c = create(clients)
    result = clients["citizen"].post(
        f"/api/complaints/{c['id']}/evidence?stage=COMPLAINT",
        files={"file": ("huge.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )
    assert result.status_code == 413
    c = resolved(clients)
    with factory() as db:
        row = db.get(Complaint, c["id"])
        row.resolved_at = now() - timedelta(days=8)
        db.commit()
    c = clients["citizen"].get(f"/api/complaints/{c['id']}").json()
    assert (
        clients["citizen"]
        .post(
            f"/api/complaints/{c['id']}/transition",
            json={"action": "reopen", "version": c["version"], "reason": "Outside allowed window"},
        )
        .status_code
        == 422
    )


def test_protected_account_creation_and_configuration(env):
    clients, _ = env
    data = {
        "name": "New Staff",
        "email": "staff@example.com",
        "password": PASSWORD,
        "role": "SUPERVISOR",
        "ward_id": 1,
    }
    assert clients["citizen"].post("/api/users", json=data).status_code == 403
    result = clients["authority"].post("/api/users", json=data)
    assert result.status_code == 201 and "password_hash" not in result.json()
    assert (
        clients["authority"]
        .post("/api/config/categories", json={"name": "Uncollected recyclable waste"})
        .status_code
        == 201
    )
    assert (
        clients["authority"]
        .post("/api/config/wards", json={"name": "New Ward", "zone": "New Zone"})
        .status_code
        == 201
    )
    assert (
        clients["authority"]
        .put("/api/config/sla", json={"priority": "URGENT", "hours": 4})
        .status_code
        == 200
    )
    assert (
        clients["supervisor"]
        .put("/api/config/sla", json={"priority": "URGENT", "hours": 4})
        .status_code
        == 403
    )

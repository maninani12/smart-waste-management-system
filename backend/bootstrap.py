"""Create the initial authority interactively; never accept a password on argv."""

from getpass import getpass

from sqlalchemy import select

from .db import SessionLocal
from .models import SLA, User
from .schemas import Register
from .security import hasher
from .services import audit


def main():
    data = Register(
        name=input("Authority name: "),
        email=input("Authority email: "),
        password=getpass("Password (12+ characters): "),
    )
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.role == "GOVERNMENT_AUTHORITY")):
            raise RuntimeError(
                "An authority already exists. Use authorized account administration."
            )
        user = User(
            name=data.name,
            email=str(data.email).lower(),
            password_hash=hasher.hash(data.password),
            role="GOVERNMENT_AUTHORITY",
        )
        db.add(user)
        db.flush()
        for priority, hours in [("LOW", 120), ("NORMAL", 72), ("HIGH", 24), ("URGENT", 8)]:
            if not db.get(SLA, priority):
                db.add(SLA(priority=priority, hours=hours))
        audit(db, user, "user.bootstrap", user.id)
        db.commit()
    print("Authority created. Sign in to configure wards, categories and staff.")


if __name__ == "__main__":
    main()

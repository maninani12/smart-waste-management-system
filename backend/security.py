import hashlib
import secrets
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session as DBSession

from .db import get_db, now
from .models import Session, User

hasher = PasswordHasher()
DUMMY_HASH = hasher.hash(secrets.token_urlsafe(32))


def digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def verify_password(encoded, password):
    try:
        return hasher.verify(encoded or DUMMY_HASH, password)
    except VerificationError:
        return False


def create_session(db, user):
    token = secrets.token_urlsafe(48)
    db.add(
        Session(token_hash=digest(token), user_id=user.id, expires_at=now() + timedelta(hours=8))
    )
    return token


def current_user(request: Request, db: DBSession = Depends(get_db)):
    token = request.cookies.get("swm_session", "")
    session = db.get(Session, digest(token))
    user = db.get(User, session.user_id) if session and session.expires_at > now() else None
    if not user or not user.active:
        raise HTTPException(401, "Please sign in again.")
    return user


def require(user, *roles):
    if user.role not in roles:
        raise HTTPException(403, "This action is not available to your role.")


def public_user(user):
    return {
        key: getattr(user, key)
        for key in ["id", "name", "email", "role", "ward_id", "active", "available"]
    }

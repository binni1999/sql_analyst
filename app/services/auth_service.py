"""Database-backed browser authentication for DataPilot.

Passwords use PBKDF2-HMAC-SHA256 and session secrets are stored only as SHA-256
hashes. The browser receives the opaque session secret in an HttpOnly cookie.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

try:
    from config import get_settings
    from database.dbconnect import engine
except ImportError:
    from app.config import get_settings
    from app.database.dbconnect import engine

settings = get_settings()
SESSION_COOKIE = "datapilot_session"
SESSION_TTL = timedelta(days=7)
PBKDF2_ITERATIONS = 310_000
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def ensure_auth_tables() -> None:
    """Create auth tables idempotently; existing application data is untouched."""
    statements = [
        """CREATE TABLE IF NOT EXISTS datapilot_users (
            id UUID PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            email VARCHAR(320) NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        """CREATE TABLE IF NOT EXISTS datapilot_auth_sessions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES datapilot_users(id) ON DELETE CASCADE,
            token_hash CHAR(64) NOT NULL UNIQUE,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_datapilot_auth_sessions_user_id ON datapilot_auth_sessions(user_id)",
        """CREATE TABLE IF NOT EXISTS datapilot_conversation_owners (
            conversation_id VARCHAR(200) PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES datapilot_users(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_datapilot_conversation_owners_user_id ON datapilot_conversation_owners(user_id)",
        """CREATE TABLE IF NOT EXISTS datapilot_login_attempts (
            id BIGSERIAL PRIMARY KEY,
            client_key CHAR(64) NOT NULL,
            attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )""",
        "CREATE INDEX IF NOT EXISTS ix_datapilot_login_attempts_key_time ON datapilot_login_attempts(client_key, attempted_at)",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, expected_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(digest.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _validate_origin(request: Request) -> None:
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") not in {item.rstrip("/") for item in settings.cors_origin_list}:
        raise HTTPException(status_code=403, detail="Request origin is not allowed")


def _new_session(user_id: str) -> str:
    token = secrets.token_urlsafe(48)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM datapilot_auth_sessions WHERE expires_at <= :now"), {"now": _now()})
        conn.execute(text("INSERT INTO datapilot_auth_sessions (id, user_id, token_hash, expires_at) VALUES (:id, :uid, :hash, :expires)"), {
            "id": str(__import__("uuid").uuid4()), "uid": user_id,
            "hash": _token_hash(token), "expires": _now() + SESSION_TTL,
        })
    return token


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE, token, max_age=int(SESSION_TTL.total_seconds()),
        httponly=True, secure=settings.environment.lower() in {"production", "prod"},
        samesite="lax", path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, samesite="lax",
                           secure=settings.environment.lower() in {"production", "prod"})


def current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        ensure_auth_tables()
        with engine.begin() as conn:
            row = conn.execute(text("""SELECT u.id::text AS id, u.name, u.email
                FROM datapilot_auth_sessions s JOIN datapilot_users u ON u.id=s.user_id
                WHERE s.token_hash=:hash AND s.expires_at > :now"""),
                {"hash": _token_hash(token), "now": _now()}).mappings().first()
            if not row:
                raise HTTPException(status_code=401, detail="Session expired or invalid")
            return dict(row)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Authentication storage is unavailable") from exc


def register_user(name: str, email: str, password: str) -> dict:
    normalized_email = email.strip().lower()
    normalized_name = name.strip()
    if not normalized_name or len(normalized_name) > 100:
        raise HTTPException(status_code=422, detail="Name must contain 1 to 100 characters")
    if len(normalized_email) > 320 or not _EMAIL_RE.fullmatch(normalized_email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if len(password) < 8 or len(password) > 128:
        raise HTTPException(status_code=422, detail="Password must be between 8 and 128 characters")
    if not any(c.isalpha() for c in password) or not any(c.isdigit() for c in password):
        raise HTTPException(status_code=422, detail="Password must contain at least one letter and one number")
    ensure_auth_tables()
    user_id = str(__import__("uuid").uuid4())
    try:
        with engine.begin() as conn:
            conn.execute(text("INSERT INTO datapilot_users (id, name, email, password_hash) VALUES (:id, :name, :email, :password_hash)"), {
                "id": user_id, "name": normalized_name, "email": normalized_email,
                "password_hash": _password_hash(password),
            })
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists") from exc
    return {"id": user_id, "name": normalized_name, "email": normalized_email}


def _client_key(client_ip: str) -> str:
    # Store only a keyed-independent hash of the address, not the raw IP.
    return hashlib.sha256(client_ip.encode()).hexdigest()


def enforce_login_rate_limit(client_ip: str) -> None:
    ensure_auth_tables()
    key = _client_key(client_ip)
    cutoff = _now() - timedelta(minutes=15)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM datapilot_login_attempts WHERE attempted_at < :cutoff"), {"cutoff": cutoff})
        count = conn.execute(text("SELECT COUNT(*) FROM datapilot_login_attempts WHERE client_key=:key AND attempted_at >= :cutoff"), {"key": key, "cutoff": cutoff}).scalar_one()
    if count >= 10:
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 15 minutes.")


def record_failed_login(client_ip: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("INSERT INTO datapilot_login_attempts (client_key) VALUES (:key)"), {"key": _client_key(client_ip)})


def clear_login_attempts(client_ip: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM datapilot_login_attempts WHERE client_key=:key"), {"key": _client_key(client_ip)})


def authenticate_user(email: str, password: str) -> dict:
    ensure_auth_tables()
    normalized_email = email.strip().lower()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id::text AS id, name, email, password_hash FROM datapilot_users WHERE email=:email"), {"email": normalized_email}).mappings().first()
    # A fixed dummy hash keeps unknown-email failures from skipping the expensive hash operation.
    if row:
        valid = _verify_password(password, row["password_hash"])
    else:
        _verify_password(password, "pbkdf2_sha256$310000$00112233445566778899aabbccddeeff$" + "0" * 64)
        valid = False
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def owns_conversation(user_id: str, conversation_id: str) -> bool:
    ensure_auth_tables()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT 1 FROM datapilot_conversation_owners WHERE conversation_id=:cid AND user_id=:uid"), {"cid": conversation_id, "uid": user_id}).first()
        return row is not None


def claim_conversation(user_id: str, conversation_id: str) -> None:
    ensure_auth_tables()
    with engine.begin() as conn:
        existing = conn.execute(text("SELECT user_id::text FROM datapilot_conversation_owners WHERE conversation_id=:cid"), {"cid": conversation_id}).scalar_one_or_none()
        if existing and existing != user_id:
            raise HTTPException(status_code=403, detail="This conversation belongs to another user")
        if not existing:
            conn.execute(text("INSERT INTO datapilot_conversation_owners (conversation_id, user_id) VALUES (:cid, :uid)"), {"cid": conversation_id, "uid": user_id})


def revoke_session(request: Request) -> None:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        ensure_auth_tables()
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM datapilot_auth_sessions WHERE token_hash=:hash"), {"hash": _token_hash(token)})

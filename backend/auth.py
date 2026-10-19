"""Local registration, password hashing, and cookie-session endpoints.

Authentication state is stored in the React/FastAPI SQLite database. This module
does not touch the Streamlit application's shared document library.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from backend.database import database_connection, initialize_database

router = APIRouter(prefix="/api/auth", tags=["authentication"])

SESSION_COOKIE = "healthai_session"
CSRF_COOKIE = "healthai_csrf"
SESSION_LIFETIME_SECONDS = 7 * 24 * 60 * 60
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)


def _cookie_secure() -> bool:
    """Enable Secure cookies when the app is served over HTTPS."""
    return os.environ.get("HEALTHAI_COOKIE_SECURE", "").strip().lower() in {
        "1", "true", "yes"
    }


def _normalise_email(email: str) -> str:
    value = email.strip().lower()
    if not _EMAIL_RE.fullmatch(value):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    return value


def _password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=64,
    )
    return f"scrypt$\{SCRYPT_N}$\{SCRYPT_R}$\{SCRYPT_P}$\{salt.hex()}$\{derived.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, n, r, p, salt_hex, expected_hex = stored_hash.split("$")
        if algorithm != "scrypt":
            return False
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(bytes.fromhex(expected_hex)),
        )
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError, MemoryError):
        return False


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _new_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.now(timezone.utc) + timedelta(seconds=SESSION_LIFETIME_SECONDS)).isoformat()
    with database_connection() as connection:
        connection.execute(
            "INSERT INTO sessions(user_id, token_hash, expires_at) VALUES (?, ?, ?)",
            (user_id, _token_hash(token), expires_at),
        )
    return token


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/api",
    )


def _require_csrf(request: Request, header_token: str | None) -> None:
    cookie_token = request.cookies.get(CSRF_COOKIE)
    if (
        not cookie_token
        or not header_token
        or not hmac.compare_digest(cookie_token, header_token)
    ):
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid. Refresh and try again.")


def _current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Please log in to continue.")

    initialize_database()
    hashed_token = _token_hash(token)
    now = datetime.now(timezone.utc)
    with database_connection() as connection:
        row = connection.execute(
            """
            SELECT users.id, users.email, sessions.expires_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ?
            """,
            (hashed_token,),
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=401, detail="Session is invalid. Please log in again.")
        try:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
        except ValueError:
            expires_at = now - timedelta(seconds=1)
        if expires_at <= now:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (hashed_token,))
            raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
        return {"id": row["id"], "email": row["email"]}


@router.get("/csrf")
def get_csrf_token(response: Response) -> dict:
    """Issue the double-submit CSRF token needed by browser write requests."""
    token = secrets.token_urlsafe(32)
    response.set_cookie(
        key=CSRF_COOKIE,
        value=token,
        max_age=SESSION_LIFETIME_SECONDS,
        httponly=False,
        secure=_cookie_secure(),
        samesite="lax",
        path="/api",
    )
    return {"csrf_token": token}


@router.post("/register", status_code=201)
def register(credentials: Credentials, request: Request, response: Response) -> dict:
    _require_csrf(request, request.headers.get("x-csrf-token"))
    email = _normalise_email(credentials.email)
    initialize_database()
    password_hash = _password_hash(credentials.password)
    try:
        with database_connection() as connection:
            cursor = connection.execute(
                "INSERT INTO users(email, password_hash) VALUES (?, ?)",
                (email, password_hash),
            )
            user_id = cursor.lastrowid
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=409, detail="An account with this email already exists.") from exc

    token = _new_session(int(user_id))
    _set_session_cookie(response, token)
    return {"user": {"id": user_id, "email": email}}


@router.post("/login")
def login(credentials: Credentials, request: Request, response: Response) -> dict:
    _require_csrf(request, request.headers.get("x-csrf-token"))
    email = _normalise_email(credentials.email)
    initialize_database()
    with database_connection() as connection:
        row = connection.execute(
            "SELECT id, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()

    if row is None or not _verify_password(credentials.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email or password is incorrect.")

    token = _new_session(row["id"])
    _set_session_cookie(response, token)
    return {"user": {"id": row["id"], "email": row["email"]}}


@router.get("/me")
def who_am_i(request: Request) -> dict:
    user = _current_user(request)
    return {"user": user}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    _require_csrf(request, request.headers.get("x-csrf-token"))
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        initialize_database()
        with database_connection() as connection:
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    response.delete_cookie(SESSION_COOKIE, path="/api", secure=_cookie_secure(), httponly=True, samesite="lax")
    response.delete_cookie(CSRF_COOKIE, path="/api", secure=_cookie_secure(), httponly=False, samesite="lax")
    return {"logged_out": True}

"""
auth.py — Google OAuth 2.0 + JWT session management for the FastAPI backend.

Flow:
  1. Frontend redirects user to GET /api/auth/login
  2. User authenticates with Google
  3. Google redirects to GET /api/auth/callback
  4. Backend exchanges code for user info, issues a signed JWT as an httpOnly cookie
  5. All protected routes read + verify that cookie via get_current_user()

Environment variables required (same .env as before, plus):
  GOOGLE_CLIENT_ID      — from Google Cloud Console
  GOOGLE_CLIENT_SECRET  — from Google Cloud Console
  SECRET_KEY            — a random secret for signing JWTs (e.g. openssl rand -hex 32)
  FRONTEND_URL          — e.g. http://localhost:5173 (for redirect after login)
  ADMIN_EMAILS          — comma-separated list of admin email addresses
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

import db
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from jose import JWTError, jwt
from starlette.responses import JSONResponse, RedirectResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# ── Config ────────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5173")
ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}

# ── OAuth client ──────────────────────────────────────────────────────────────
oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID", ""),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET", ""),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


# ── JWT helpers ───────────────────────────────────────────────────────────────
def _create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def _verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or not stored_hash.startswith("pbkdf2_sha256$"):
        return False
    try:
        _, salt, expected = stored_hash.split("$", 2)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200000)
        return hmac.compare_digest(digest.hex(), expected)
    except (TypeError, ValueError):
        return False


def _session_response(user: dict) -> JSONResponse:
    jwt_token = _create_token({
        "email": user["email"],
        "name": user.get("name", user["email"]),
        "picture": user.get("picture", ""),
        "is_admin": user.get("is_admin", False),
    })
    response = JSONResponse(content={
        "ok": True,
        "user": {
            "email": user["email"],
            "name": user.get("name", user["email"]),
            "picture": user.get("picture", ""),
            "is_admin": user.get("is_admin", False),
        },
    })
    response.set_cookie(
        key="session_token",
        value=jwt_token,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_EXPIRE_HOURS * 3600,
    )
    return response


# ── Dependency: get logged-in user ────────────────────────────────────────────
def get_current_user(session_token: str = Cookie(default=None)) -> dict:
    """FastAPI dependency — raises 401 if the user is not logged in."""
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = _decode_token(session_token)
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")


def get_admin_user(user: dict = Depends(get_current_user)) -> dict:
    """FastAPI dependency — raises 403 if the user is not an admin."""
    if user.get("email", "").lower() not in ADMIN_EMAILS:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# ── Routes ────────────────────────────────────────────────────────────────────
@router.post("/signup")
async def signup(payload: dict):
    """Register a user with email/password and immediately create a session."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid signup payload")

    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not name or not email or not password:
        raise HTTPException(status_code=400, detail="Name, email, and password are required")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address")

    if db.get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    db.create_user(email, _hash_password(password), name=name, is_admin=email in ADMIN_EMAILS)
    user = db.get_user_by_email(email)
    return _session_response({
        "email": user["email"],
        "name": user["name"],
        "picture": "",
        "is_admin": bool(user.get("is_admin")),
    })


@router.post("/login")
async def login(payload: dict):
    """Authenticate a user with email/password and create a session."""
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid login payload")

    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required")

    user = db.get_user_by_email(email)
    if not user or not _verify_password(password, user.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    return _session_response({
        "email": user["email"],
        "name": user.get("name") or email,
        "picture": "",
        "is_admin": bool(user.get("is_admin")),
    })


@router.get("/login")
async def google_login(request: Request):
    """Redirect the browser to Google's OAuth consent screen."""
    redirect_uri = os.environ.get("GOOGLE_REDIRECT_URI") or (str(request.base_url) + "api/auth/callback")
    logger.info(f"Redirecting with URI = {redirect_uri}")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request, response: Response):
    """Exchange the OAuth code for user info, mint a JWT, and redirect to frontend."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.exception("OAuth callback failed")
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")

    user_info = token.get("userinfo") or {}
    email = (user_info.get("email") or "").lower()
    name = user_info.get("name", email)
    picture = user_info.get("picture", "")

    if not email:
        raise HTTPException(status_code=400, detail="Could not retrieve email from Google")

    jwt_token = _create_token({
        "email": email,
        "name": name,
        "picture": picture,
        "is_admin": email in ADMIN_EMAILS,
    })

    redirect = RedirectResponse(url=FRONTEND_URL)
    redirect.set_cookie(
        key="session_token",
        value=jwt_token,
        httponly=True,
        samesite="lax",
        max_age=TOKEN_EXPIRE_HOURS * 3600,
    )
    return redirect


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Return the currently logged-in user's info (used by the React app on startup)."""
    return {
        "email": user["email"],
        "name": user.get("name", user["email"]),
        "picture": user.get("picture", ""),
        "is_admin": user.get("is_admin", False),
    }


@router.post("/logout")
async def logout(response: Response):
    """Clear the session cookie."""
    response.delete_cookie("session_token")
    return {"ok": True}
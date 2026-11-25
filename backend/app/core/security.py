"""Single-operator authentication for the dashboard and administrative API."""
import base64
import hashlib
import hmac
import json
import secrets
import time
from contextvars import ContextVar
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Operator session"])
_actor = ContextVar("operator", default="system")
_attempts: dict[str, list[float]] = {}
COOKIE = "impex_session"

def reviewer_identity() -> str:
    return _actor.get()

def _signature(value: str) -> str:
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()

def _session(user: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"user": user, "expires": int(time.time()) + 3600}).encode()).decode()
    return payload + "." + _signature(payload)

async def require_operator(request: Request) -> str:
    if request.url.path in {"/api/v1/health", "/api/v1/auth/login"}:
        return "anonymous"
    if not settings.ADMIN_PASSWORD:
        raise HTTPException(503, "Operator credentials are not configured.")
    authorization = request.headers.get("authorization", "")
    if authorization.startswith("Bearer ") and secrets.compare_digest(authorization[7:], settings.ADMIN_PASSWORD):
        _actor.set(settings.ADMIN_USERNAME)
        return settings.ADMIN_USERNAME
    try:
        payload, signature = request.cookies.get(COOKIE, "").rsplit(".", 1)
        if not hmac.compare_digest(signature, _signature(payload)):
            raise ValueError()
        session = json.loads(base64.urlsafe_b64decode(payload))
        if session["expires"] < time.time() or session["user"] != settings.ADMIN_USERNAME:
            raise ValueError()
    except (ValueError, KeyError, TypeError):
        raise HTTPException(401, "Sign in to continue.")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        if request.headers.get("x-requested-with") != "impex-ui":
            raise HTTPException(403, "Missing request protection header.")
        if request.headers.get("origin") not in {str(request.base_url).rstrip("/"), *settings.cors_origins}:
            raise HTTPException(403, "Request origin is not allowed.")
    _actor.set(session["user"])
    return session["user"]

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=512)

@router.post("/login")
def login(req: Login, request: Request, response: Response):
    origin = request.headers.get("origin")
    if origin and origin not in {str(request.base_url).rstrip("/"), *settings.cors_origins}:
        raise HTTPException(403, "Request origin is not allowed.")
    if not settings.ADMIN_PASSWORD:
        raise HTTPException(503, "Operator credentials are not configured.")
    client = request.client.host if request.client else "unknown"
    now = time.monotonic()
    recent = [t for t in _attempts.get(client, []) if now - t < 300]
    if len(recent) >= 5:
        raise HTTPException(429, "Too many sign-in attempts. Try again in five minutes.")
    if not (secrets.compare_digest(req.username, settings.ADMIN_USERNAME) and secrets.compare_digest(req.password, settings.ADMIN_PASSWORD)):
        _attempts[client] = recent + [now]
        raise HTTPException(401, "Invalid sign-in credentials.")
    _attempts.pop(client, None)
    response.set_cookie(COOKIE, _session(req.username), httponly=True, secure=settings.APP_ENV == "production", samesite="strict", max_age=3600, path="/")
    response.headers["Cache-Control"] = "no-store"
    return {"username": req.username}

@router.get("/session")
def session(user: str = Depends(require_operator)):
    return {"username": user}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE, path="/")
    return {"signed_out": True}

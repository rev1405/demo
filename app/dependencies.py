"""Shared FastAPI dependencies: session user, role gates, rate limiter.
[SSDLC: authorization + abuse resistance]"""
import time

from bson import ObjectId
from fastapi import Depends, HTTPException, Request

from app.core.database import get_db
from app.core.security import verify_token

SESSION_COOKIE = "mallhaul_session"

_BUCKETS: dict[str, list[float]] = {}


def rate_limit(limit: int = 10, per_seconds: int = 60):
    """Fixed-window limiter per IP+path. Protects auth and money endpoints."""
    def dep(request: Request):
        ip = request.client.host if request.client else "?"
        key = f"{request.url.path}|{ip}"
        now = time.time()
        q = _BUCKETS.setdefault(key, [])
        while q and q[0] < now - per_seconds:
            q.pop(0)
        if len(q) >= limit:
            raise HTTPException(429, "Too many requests. Try again shortly.")
        q.append(now)
    return dep


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    uid = verify_token(token) if token else None
    if not uid:
        raise HTTPException(401, "Sign in required")
    user = get_db().users.find_one({"_id": uid})
    if not user or not user.get("is_active", True):
        raise HTTPException(401, "Account unavailable")
    return user


def require_customer(u: dict = Depends(get_current_user)) -> dict:
    if "CUSTOMER" not in u.get("roles", []):
        raise HTTPException(403, "Customer account required")
    return u


def get_customer_doc(u: dict = Depends(require_customer)) -> dict:
    c = get_db().customers.find_one({"user_id": u["_id"]})
    if not c:
        raise HTTPException(403, "No customer profile")
    return c


def require_ops(u: dict = Depends(get_current_user)) -> dict:
    allowed = {"STORE_MANAGER", "FULFILLMENT_STAFF", "MALL_ADMIN", "SYSTEM_ADMIN"}
    if not allowed & set(u.get("roles", [])):
        raise HTTPException(403, "Operations role required")
    return u
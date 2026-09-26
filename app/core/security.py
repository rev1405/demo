"""Password hashing + signed session tokens.
[SSDLC] Passwords: PBKDF2-SHA256, 390k iterations, per-user salt. Never plaintext.
[SSDLC] Sessions: HMAC-signed token in an HttpOnly SameSite cookie (set in auth router).
"""
import hashlib
import hmac
import os
import time

from app.core.config import settings

_ITERATIONS = 390_000


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _scheme, iters, salt_hex, dk_hex = stored.split("$")
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(iters))
        return hmac.compare_digest(dk.hex(), dk_hex)
    except Exception:
        return False


def _sig(message: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), message.encode(),
                    hashlib.sha256).hexdigest()


def create_token(user_id, ttl_seconds: int = 60 * 60 * 24 * 7) -> str:
    exp = int(time.time()) + ttl_seconds
    msg = f"{user_id}.{exp}"
    return f"{msg}.{_sig(msg)}"


def verify_token(token: str):
    """Returns ObjectId user id or None. Constant-time signature compare."""
    try:
        uid, exp, sig = token.rsplit(".", 2)
        if not hmac.compare_digest(_sig(f"{uid}.{exp}"), sig):
            return None
        if int(exp) < time.time():
            return None
        from bson import ObjectId
        return ObjectId(uid)
    except Exception:
        return None
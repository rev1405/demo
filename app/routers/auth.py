# [DB CONNECTION] collections: users, customers, wallets, carts
from datetime import datetime, timezone

from bson import ObjectId
from bson.decimal128 import Decimal128
from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.database import get_db
from app.core.security import create_token, hash_password, verify_password
from app.dependencies import SESSION_COOKIE, get_current_user, rate_limit
from app.schemas import LoginIn, RegisterIn
from app.utils import clean

router = APIRouter(prefix="/api/auth", tags=["auth"])
D = lambda v: Decimal128(str(v))
now = lambda: datetime.now(timezone.utc)


def _set_session(response: Response, user_id):
    # [SSDLC] HttpOnly + SameSite=Lax. Add secure=True when served over HTTPS.
    response.set_cookie(SESSION_COOKIE, create_token(user_id),
                        max_age=60 * 60 * 24 * 7, httponly=True,
                        samesite="lax", path="/")


@router.post("/register", status_code=201)
def register(data: RegisterIn, response: Response,
             _rl: None = Depends(rate_limit(limit=10))):
    db = get_db()
    email = data.email.lower()
    if db.users.find_one({"email": email}):
        raise HTTPException(409, "Email already registered")
    uid = ObjectId()
    db.users.insert_one({
        "_id": uid, "first_name": data.first_name.strip(),
        "last_name": data.last_name.strip() or None,
        "email": email, "phone": data.phone.strip(),
        "password_hash": hash_password(data.password),     # never plaintext
        "roles": ["CUSTOMER"], "is_active": True,
        "created_at": now(), "updated_at": now()})
    cid = ObjectId()
    db.customers.insert_one({"_id": cid, "user_id": uid,
                             "default_address_id": None,
                             "created_at": now(), "updated_at": now()})
    db.wallets.insert_one({"_id": ObjectId(), "user_id": uid,
                           "balance": D("0"), "currency": "ZAR",
                           "created_at": now(), "updated_at": now()})
    _set_session(response, uid)
    return clean({"user_id": uid, "customer_id": cid})


@router.post("/login")
def login(data: LoginIn, response: Response,
          _rl: None = Depends(rate_limit(limit=10))):
    db = get_db()
    user = db.users.find_one({"email": data.email.lower()})
    if not user or not verify_password(data.password,
                                       user.get("password_hash") or ""):
        # [SSDLC] generic message: no user enumeration
        raise HTTPException(401, "Invalid email or password")
    db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login_at": now()}})
    _set_session(response, user["_id"])
    return clean({"user_id": user["_id"], "roles": user["roles"]})


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(u: dict = Depends(get_current_user)):
    db = get_db()
    customer = db.customers.find_one({"user_id": u["_id"]})
    wallet = db.wallets.find_one({"user_id": u["_id"]}) or {"balance": D("0")}
    cart = db.carts.find_one({"customer_id": (customer or {}).get("_id"),
                              "status": "ACTIVE"}) or {"items": []}
    return clean({"user_id": u["_id"], "first_name": u["first_name"],
                  "email": u["email"], "roles": u.get("roles", []),
                  "customer_id": (customer or {}).get("_id"),
                  "default_address_id": (customer or {}).get("default_address_id"),
                  "wallet_balance": wallet["balance"],
                  "cart_items": sum(i["quantity"] for i in cart.get("items", []))})
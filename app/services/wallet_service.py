# [DB CONNECTION] collections: wallets, wallet_transactions, audit_logs
# MVP payment simulation. Production: replace charge/refund internals with a
# payment service provider - the call sites stay identical (see BUSINESS_CASE.md).
from datetime import datetime, timezone

from bson import ObjectId
from bson.decimal128 import Decimal128
from fastapi import HTTPException

from app.utils import to_float

D = lambda v: Decimal128(str(v))
now = lambda: datetime.now(timezone.utc)


def get_wallet(db, user_id) -> dict:
    w = db.wallets.find_one({"user_id": user_id})
    if not w:
        db.wallets.insert_one({"_id": ObjectId(), "user_id": user_id,
                               "balance": D("0"), "currency": "ZAR",
                               "created_at": now(), "updated_at": now()})
        w = db.wallets.find_one({"user_id": user_id})
    return w


def _tx(db, user_id, tx_type, amount, ref=None, order_id=None):
    db.wallet_transactions.insert_one({
        "_id": ObjectId(), "user_id": user_id, "type": tx_type,
        "amount": D(amount), "ref": ref, "order_id": order_id,
        "created_at": now()})


def top_up(db, user_id, amount, actor_id=None):
    amount = to_float(amount)
    if not (10 <= amount <= 5000):
        raise HTTPException(400, "Top-up must be between R10 and R5000")
    db.wallets.update_one({"user_id": user_id},
                          {"$inc": {"balance": D(amount)},
                           "$set": {"updated_at": now()}})
    _tx(db, user_id, "TOPUP", amount, ref="DEMO_GATEWAY")
    db.audit_logs.insert_one({"_id": ObjectId(), "user_id": actor_id,
                              "action": "WALLET_TOPUP", "entity_type": "WALLET",
                              "entity_id": user_id, "changes": {"amount": amount},
                              "timestamp": now()})
    return get_wallet(db, user_id)


def charge(db, user_id, amount, order_id):
    """Atomic guarded debit: balance only drops if funds are sufficient."""
    amount = to_float(amount)
    res = db.wallets.update_one(
        {"user_id": user_id, "balance": {"$gte": D(amount)}},
        {"$inc": {"balance": D(-amount)}, "$set": {"updated_at": now()}})
    if res.modified_count == 0:
        raise HTTPException(402, "Insufficient wallet balance")
    _tx(db, user_id, "PAYMENT", -amount, order_id=order_id)


def refund(db, user_id, amount, order_id, refund_id=None):
    amount = to_float(amount)
    db.wallets.update_one({"user_id": user_id},
                          {"$inc": {"balance": D(amount)},
                           "$set": {"updated_at": now()}})
    _tx(db, user_id, "REFUND", amount,
        ref=str(refund_id) if refund_id else None, order_id=order_id)
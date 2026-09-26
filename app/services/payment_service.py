"""Payment webhook handler - runs in its own transaction. Idempotent:
guarded transition PENDING -> SUCCESS; replays are no-ops.
[DB CONNECTION] collections: payments, orders, payment_splits, audit_logs"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.decimal128 import Decimal128

from app.utils import to_float

D = lambda v: Decimal128(str(v))
now = lambda: datetime.now(timezone.utc)


def mark_payment_paid(db, payment_id: ObjectId, provider_txn_id: str) -> None:
    with db.client.start_session() as s:
        s.start_transaction()
        try:
            p = db.payments.find_one_and_update(
                {"_id": payment_id, "status": "PENDING"},          # guard = idempotent
                {"$set": {"status": "SUCCESS",
                          "provider_transaction_id": provider_txn_id,
                          "paid_at": now(), "updated_at": now()}},
                session=s)
            if not p:
                s.abort_transaction()
                return

            order = db.orders.find_one({"_id": p["order_id"]}, session=s)

            splits = [{
                "_id": ObjectId(),
                "payment_id": payment_id,
                "order_id": order["_id"],
                "store_id": m["store_id"],
                "gross_amount": m["merchant_amount"],
                "platform_fee": m["platform_fee"],
                "net_amount": D(to_float(m["merchant_amount"]) - to_float(m["platform_fee"])),
                "status": "HELD",
                "released_at": None,
                "created_at": now(),
                "updated_at": now(),
            } for m in order["merchants"]]
            db.payment_splits.insert_many(splits, session=s)

            db.orders.update_one(
                {"_id": order["_id"]},
                {"$set": {"payment_status": "PAID",
                          "order_status": "PROCESSING", "updated_at": now()}},
                session=s)

            db.audit_logs.insert_one({
                "_id": ObjectId(), "user_id": None,
                "action": "PAYMENT_STATUS_CHANGED",
                "entity_type": "PAYMENT", "entity_id": payment_id,
                "changes": {"status": {"old": "PENDING", "new": "SUCCESS"}},
                "timestamp": now()}, session=s)

            s.commit_transaction()
        except Exception:
            s.abort_transaction()
            raise
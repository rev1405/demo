"""Order cancellation: cancel order -> release reserved inventory ->
create refund record (never overwrite the payment) -> audit.
[DB CONNECTION] collections: orders, mall_inventory, payments, refunds, audit_logs"""
from datetime import datetime, timezone

from bson import ObjectId

now = lambda: datetime.now(timezone.utc)

_CANCELLABLE = ("PENDING", "PROCESSING", "PARTIALLY_READY", "READY_FOR_DELIVERY")


def cancel_order(db, order_id: ObjectId) -> None:
    with db.client.start_session() as s:
        s.start_transaction()
        try:
            order = db.orders.find_one({"_id": order_id}, session=s)
            if not order:
                raise ValueError("Order not found")
            if order["order_status"] not in _CANCELLABLE:
                raise ValueError("Order can no longer be cancelled")

            for m in order["merchants"]:
                if m["fulfillment_status"] in ("HANDED_TO_DRIVER", "COMPLETED"):
                    continue
                db.orders.update_one(
                    {"_id": order_id, "merchants.store_id": m["store_id"]},
                    {"$set": {"merchants.$.fulfillment_status": "CANCELLED"}},
                    session=s)
                for item in m["items"]:          # release reserved stock
                    db.mall_inventory.update_one(
                        {"product_id": item["product_id"], "store_id": m["store_id"]},
                        {"$inc": {"quantity_reserved": -item["quantity"]},
                         "$set": {"updated_at": now()}},
                        session=s)

            db.orders.update_one(
                {"_id": order_id},
                {"$set": {"order_status": "CANCELLED", "updated_at": now()}},
                session=s)

            pay = db.payments.find_one(
                {"order_id": order_id, "status": "SUCCESS"}, session=s)
            if pay:
                db.refunds.insert_one({
                    "_id": ObjectId(), "payment_id": pay["_id"],
                    "order_id": order_id, "amount": pay["amount"],
                    "reason": "ORDER_CANCELLED", "status": "PENDING",
                    "provider_refund_id": None,
                    "created_at": now(), "updated_at": now()}, session=s)
                db.orders.update_one(
                    {"_id": order_id},
                    {"$set": {"payment_status": "REFUND_PENDING"}}, session=s)

            db.audit_logs.insert_one({
                "_id": ObjectId(), "user_id": None,
                "action": "ORDER_STATUS_CHANGED",
                "entity_type": "ORDER", "entity_id": order_id,
                "changes": {"order_status": {"old": order["order_status"],
                                             "new": "CANCELLED"}},
                "timestamp": now()}, session=s)

            s.commit_transaction()
        except Exception:
            s.abort_transaction()
            raise
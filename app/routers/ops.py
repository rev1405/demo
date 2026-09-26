# [DB CONNECTION] collections: orders, packages, deliveries, audit_logs
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from database.enums import FULFILLMENT_TRANSITIONS, FulfillmentStatus
from app.dependencies import require_ops
from app.schemas import DeliveryStatusIn, MerchantStatusIn
from app.services import delivery_service
from app.utils import clean

router = APIRouter(prefix="/api/ops", tags=["operations"])
now = lambda: datetime.now(timezone.utc)


def _recompute_order_status(db, order_id):
    o = db.orders.find_one({"_id": order_id})
    sts = [m["fulfillment_status"] for m in o["merchants"]]
    n = len(sts)
    ready = sum(1 for s in sts if s in ("READY", "HANDED_TO_DRIVER", "COMPLETED"))
    if all(s == "CANCELLED" for s in sts):
        new = "CANCELLED"
    elif ready == n:
        new = "READY_FOR_DELIVERY"
    elif ready > 0:
        new = "PARTIALLY_READY"
    elif any(s != "PENDING" for s in sts):
        new = "PROCESSING"
    else:
        new = "PENDING"
    if o["order_status"] not in ("OUT_FOR_DELIVERY", "DELIVERED", "CANCELLED"):
        db.orders.update_one({"_id": order_id},
                             {"$set": {"order_status": new, "updated_at": now()}})


@router.post("/orders/{order_id}/stores/{store_id}/status")
def set_merchant_status(order_id: str, store_id: str, data: MerchantStatusIn,
                        ops: dict = Depends(require_ops)):
    db = get_db()
    oid, sid = ObjectId(order_id), ObjectId(store_id)
    order = db.orders.find_one({"_id": oid, "merchants.store_id": sid})
    if not order:
        raise HTTPException(404, "Order/store allocation not found")
    current = next(m["fulfillment_status"] for m in order["merchants"]
                   if m["store_id"] == sid)
    target = FulfillmentStatus(data.status)
    if target not in FULFILLMENT_TRANSITIONS[FulfillmentStatus(current)]:
        raise HTTPException(409, f"Illegal transition {current} -> {target.value}")
    db.orders.update_one({"_id": oid, "merchants.store_id": sid},
                         {"$set": {"merchants.$.fulfillment_status": target.value,
                                   "updated_at": now()}})
    _recompute_order_status(db, oid)
    db.audit_logs.insert_one({
        "_id": ObjectId(), "user_id": ops["_id"],
        "action": "FULFILLMENT_STATUS_CHANGED", "entity_type": "ORDER",
        "entity_id": oid,
        "changes": {"fulfillment_status": {"old": current, "new": target.value}},
        "timestamp": now()})
    return clean(db.orders.find_one({"_id": oid}))


@router.post("/packages/{package_id}/{action}")
def package_action(package_id: str, action: str,
                   ops: dict = Depends(require_ops)):
    db = get_db()
    pid = ObjectId(package_id)
    pkg = db.packages.find_one({"_id": pid})
    if not pkg:
        raise HTTPException(404, "Package not found")
    flow = {"receive": ({"PENDING", "READY"}, "RECEIVED", "received_at"),
            "consolidate": ({"RECEIVED"}, "CONSOLIDATED", "consolidated_at"),
            "dispatch": ({"CONSOLIDATED"}, "DISPATCHED", "dispatched_at")}
    if action not in flow:
        raise HTTPException(400, "Unknown action")
    allowed, target, stamp = flow[action]
    if pkg["status"] not in allowed:
        raise HTTPException(409, f"Cannot {action} a {pkg['status']} package")
    db.packages.update_one({"_id": pid},
                           {"$set": {"status": target, stamp: now(),
                                     "updated_at": now()}})
    db.audit_logs.insert_one({
        "_id": ObjectId(), "user_id": ops["_id"],
        "action": f"PACKAGE_{target}", "entity_type": "PACKAGE",
        "entity_id": pid,
        "changes": {"status": {"old": pkg["status"], "new": target}},
        "timestamp": now()})
    return {"package_id": str(pid), "status": target}


@router.post("/deliveries/{delivery_id}/assign")
def assign(delivery_id: str, ops: dict = Depends(require_ops)):
    db = get_db()
    delivery = db.deliveries.find_one({"_id": ObjectId(delivery_id)})
    if not delivery:
        raise HTTPException(404, "Delivery not found")
    if delivery["status"] != "PENDING":
        raise HTTPException(409, "Delivery already assigned")
    report = delivery_service.assign_courier(db, delivery)
    return {"delivery_id": delivery_id, "status": "ASSIGNED",
            "optimizer_report": clean(report)}


@router.post("/deliveries/{delivery_id}/status")
def delivery_status(delivery_id: str, data: DeliveryStatusIn,
                    ops: dict = Depends(require_ops)):
    db = get_db()
    delivery = db.deliveries.find_one({"_id": ObjectId(delivery_id)})
    if not delivery:
        raise HTTPException(404, "Delivery not found")
    delivery_service.transition(db, delivery, data.status, actor_id=ops["_id"])
    return {"delivery_id": delivery_id, "status": data.status}
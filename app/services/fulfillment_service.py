"""Packages per store, one PENDING delivery, master + package QR codes.
[DB CONNECTION] collections: packages, deliveries, qr_codes, notifications,
fulfillment_hubs, counters, customers, audit_logs"""
import secrets
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import HTTPException
from pymongo import ReturnDocument

now = lambda: datetime.now(timezone.utc)


def _seq(db, key, session=None):
    return db.counters.find_one_and_update(
        {"_id": key}, {"$inc": {"seq": 1}}, upsert=True,
        return_document=ReturnDocument.AFTER, session=session)["seq"]


def new_qr_code() -> str:
    # [SSDLC] QR payloads carry only an opaque random code; nothing sensitive.
    # secrets module = CSPRNG (roadmap: quantum RNG - docs/QUANTUM.md).
    return f"MH-QR-{secrets.token_urlsafe(9)}"


def create_fulfillment(db, order: dict) -> dict:
    hub = db.fulfillment_hubs.find_one({"mall_id": order["mall_id"],
                                        "is_active": True})
    if not hub:
        raise HTTPException(500, "No fulfillment hub configured for this mall")
    package_count = 0
    qr_rows = []
    for m in order["merchants"]:
        pid = ObjectId()
        db.packages.insert_one({
            "_id": pid, "order_id": order["_id"], "store_id": m["store_id"],
            "package_number": f"PKG-{_seq(db, 'package_number'):04d}",
            "items": [{"product_id": i["product_id"], "quantity": i["quantity"]}
                      for i in m["items"]],
            "status": "PENDING", "fulfillment_hub_id": hub["_id"],
            "received_at": None, "consolidated_at": None, "dispatched_at": None,
            "created_at": now(), "updated_at": now()})
        qr_rows.append({"entity_type": "PACKAGE", "entity_id": pid})
        package_count += 1
    did = ObjectId()
    db.deliveries.insert_one({
        "_id": did, "order_id": order["_id"],
        "driver_id": None, "runner_id": None, "vehicle_id": None,
        "pickup": hub.get("location"),
        "dropoff": order["delivery_address_snapshot"].get("location"),
        "status": "PENDING", "estimated_delivery_time": None,
        "created_at": now(), "updated_at": now()})
    qr_rows.append({"entity_type": "ORDER", "entity_id": order["_id"]})
    qr_rows.append({"entity_type": "DELIVERY", "entity_id": did})
    for row in qr_rows:
        db.qr_codes.insert_one({
            "_id": ObjectId(), "entity_type": row["entity_type"],
            "entity_id": row["entity_id"], "code": new_qr_code(),
            "status": "ACTIVE", "expires_at": None, "scanned_at": None,
            "created_at": now()})
    cust = db.customers.find_one({"_id": order["customer_id"]})
    db.notifications.insert_one({
        "_id": ObjectId(), "user_id": cust["user_id"], "type": "ORDER_STATUS",
        "title": "Order confirmed",
        "message": f"Order {order['order_number']} is being prepared.",
        "reference": {"entity_type": "ORDER", "entity_id": order["_id"]},
        "is_read": False, "read_at": None, "created_at": now()})
    db.audit_logs.insert_one({
        "_id": ObjectId(), "user_id": None, "action": "FULFILLMENT_CREATED",
        "entity_type": "ORDER", "entity_id": order["_id"],
        "changes": {"packages": package_count}, "timestamp": now()})
    return {"delivery_id": did, "package_count": package_count}
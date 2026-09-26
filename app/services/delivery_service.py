"""Courier assignment (quantum-inspired optimizer) + delivery state machine.
[DB CONNECTION] collections: deliveries, delivery_tracking, drivers, runners,
vehicles, orders, notifications, audit_logs"""
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi import HTTPException

from database.enums import DELIVERY_TRANSITIONS, DeliveryStatus
from app.services.quantum_optimizer import select_courier

now = lambda: datetime.now(timezone.utc)


def _coll(kind: str) -> str:
    return "drivers" if kind == "DRIVER" else "runners"


def _track(db, delivery_id, status, location=None, notes=None):
    db.delivery_tracking.insert_one({
        "_id": ObjectId(), "delivery_id": delivery_id, "status": status,
        "location": location, "notes": notes, "timestamp": now()})


def assign_courier(db, delivery: dict) -> dict:
    """Pick the best available courier with the quantum-inspired optimizer."""
    pickup = delivery.get("pickup")
    if not pickup:
        raise HTTPException(400, "Delivery has no pickup location")
    candidates = []
    for coll, kind in (("drivers", "DRIVER"), ("runners", "RUNNER")):
        for doc in db[coll].find({"status": "AVAILABLE", "is_active": True,
                                  "current_location": {"$ne": None}}):
            doc["kind"] = kind
            candidates.append(doc)
    if not candidates:
        raise HTTPException(409, "No couriers available right now")

    chosen, report = select_courier(pickup, candidates)
    updates = {"status": DeliveryStatus.ASSIGNED.value,
               "estimated_delivery_time": now() + timedelta(minutes=35),
               "updated_at": now()}
    if chosen["kind"] == "DRIVER":
        updates["driver_id"] = chosen["_id"]
        veh = db.vehicles.find_one({"driver_id": chosen["_id"], "is_active": True})
        if veh:
            updates["vehicle_id"] = veh["_id"]
    else:
        updates["runner_id"] = chosen["_id"]
    db.deliveries.update_one({"_id": delivery["_id"], "status": "PENDING"},
                             {"$set": updates})
    db[_coll(chosen["kind"])].update_one(
        {"_id": chosen["_id"]}, {"$set": {"status": "ON_DELIVERY"}})
    _track(db, delivery["_id"], "ASSIGNED",
           notes=f"courier={chosen['kind']} distance_m={report['best_energy_m']}")
    db.audit_logs.insert_one({
        "_id": ObjectId(), "user_id": None,
        "action": "QUANTUM_COURIER_ASSIGNED", "entity_type": "DELIVERY",
        "entity_id": delivery["_id"], "changes": report, "timestamp": now()})
    return report


def transition(db, delivery: dict, new_status: str, notes: str | None = None,
               actor_id=None):
    current = DeliveryStatus(delivery["status"])
    target = DeliveryStatus(new_status)
    if target not in DELIVERY_TRANSITIONS[current]:
        raise HTTPException(
            409, f"Illegal delivery transition {current.value} -> {target.value}")
    setd = {"status": target.value, "updated_at": now()}
    if target == DeliveryStatus.PICKED_UP:
        setd["picked_up_at"] = now()
    if target == DeliveryStatus.DELIVERED:
        setd["delivered_at"] = now()
    db.deliveries.update_one({"_id": delivery["_id"]}, {"$set": setd})
    _track(db, delivery["_id"], target.value, notes=notes)

    order_id = delivery["order_id"]
    if target == DeliveryStatus.OUT_FOR_DELIVERY:
        db.orders.update_one({"_id": order_id},
                             {"$set": {"order_status": "OUT_FOR_DELIVERY",
                                       "updated_at": now()}})
    if target in (DeliveryStatus.DELIVERED, DeliveryStatus.FAILED,
                  DeliveryStatus.CANCELLED):
        for field, coll in (("driver_id", "drivers"), ("runner_id", "runners")):
            if delivery.get(field):
                db[coll].update_one({"_id": delivery[field]},
                                    {"$set": {"status": "AVAILABLE"}})
    if target == DeliveryStatus.DELIVERED:
        order = db.orders.find_one({"_id": order_id})
        for m in order["merchants"]:
            db.orders.update_one(
                {"_id": order_id, "merchants.store_id": m["store_id"]},
                {"$set": {"merchants.$.fulfillment_status": "COMPLETED"}})
        db.orders.update_one({"_id": order_id},
                             {"$set": {"order_status": "DELIVERED",
                                       "updated_at": now()}})
        cust = db.customers.find_one({"_id": order["customer_id"]})
        db.notifications.insert_one({
            "_id": ObjectId(), "user_id": cust["user_id"], "type": "DELIVERY",
            "title": "Order delivered",
            "message": f"Order {order['order_number']} has been delivered.",
            "reference": {"entity_type": "ORDER", "entity_id": order_id},
            "is_read": False, "read_at": None, "created_at": now()})
    db.audit_logs.insert_one({
        "_id": ObjectId(), "user_id": actor_id,
        "action": "DELIVERY_STATUS_CHANGED", "entity_type": "DELIVERY",
        "entity_id": delivery["_id"],
        "changes": {"status": {"old": current.value, "new": target.value}},
        "timestamp": now()})
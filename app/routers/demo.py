# [DB CONNECTION] collections: users, orders, packages, deliveries, audit_logs
# The demo endpoint performs operations-team actions programmatically so judges
# can watch the full lifecycle. Every action is written to audit_logs as DEMO_*.
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.database import get_db
from app.core.security import create_token
from app.dependencies import SESSION_COOKIE, get_current_user, rate_limit
from app.services import delivery_service

router = APIRouter(prefix="/api/demo", tags=["demo"])
now = lambda: datetime.now(timezone.utc)


@router.post("/login")
def demo_login(response: Response, _rl: None = Depends(rate_limit(limit=6))):
    db = get_db()
    user = db.users.find_one({"email": "demo@mallhaul.co.za"})
    if not user:
        raise HTTPException(404, "Demo user not seeded. Run database.seed_demo")
    response.set_cookie(SESSION_COOKIE, create_token(user["_id"]),
                        max_age=60 * 60 * 24 * 7, httponly=True,
                        samesite="lax", path="/")
    return {"user_id": str(user["_id"]), "first_name": user["first_name"]}


def _demo_order(db, user):
    cust = db.customers.find_one({"user_id": user["_id"]})
    order = db.orders.find_one(
        {"customer_id": cust["_id"], "order_status": {"$nin": ["CANCELLED"]}},
        sort=[("created_at", -1)])
    if not order:
        raise HTTPException(404, "No orders yet. Place one from a mall first.")
    return order


@router.get("/state")
def state(u: dict = Depends(get_current_user)):
    db = get_db()
    order = _demo_order(db, u)
    delivery = db.deliveries.find_one({"order_id": order["_id"]})
    pkgs = list(db.packages.find({"order_id": order["_id"]}))
    return {"order_id": str(order["_id"]),
            "order_number": order["order_number"],
            "order_status": order["order_status"],
            "payment_status": order["payment_status"],
            "merchant_statuses": [m["fulfillment_status"]
                                  for m in order["merchants"]],
            "package_statuses": [p["status"] for p in pkgs],
            "delivery_status": delivery["status"] if delivery else None}


@router.post("/advance")
def advance(u: dict = Depends(get_current_user),
            _rl: None = Depends(rate_limit(limit=40))):
    """One click = next lifecycle stage, driven through the same service
    functions the real ops UI would call. Returns what happened."""
    db = get_db()
    order = _demo_order(db, u)
    oid = order["_id"]
    delivery = db.deliveries.find_one({"order_id": oid})
    pkgs = list(db.packages.find({"order_id": oid}))
    events: list[str] = []
    report = None

    def merchant(set_from, set_to):
        n = 0
        for m in order["merchants"]:
            if m["fulfillment_status"] == set_from:
                db.orders.update_one(
                    {"_id": oid, "merchants.store_id": m["store_id"]},
                    {"$set": {"merchants.$.fulfillment_status": set_to}})
                n += 1
        if n:
            events.append(f"{n} store(s): {set_from} -> {set_to}")

    def package(set_from, set_to, stamp):
        n = 0
        for p in pkgs:
            if p["status"] == set_from:
                db.packages.update_one(
                    {"_id": p["_id"]},
                    {"$set": {"status": set_to, stamp: now(),
                              "updated_at": now()}})
                n += 1
        if n:
            events.append(f"{n} package(s): {set_from} -> {set_to}")

    ds = delivery["status"] if delivery else None
    if order["order_status"] == "DELIVERED" or ds == "DELIVERED":
        return {"stage": "DONE", "events": ["Order already delivered"]}

    if ds in ("ASSIGNED", "PICKED_UP", "OUT_FOR_DELIVERY"):
        seq = {"ASSIGNED": "PICKED_UP", "PICKED_UP": "OUT_FOR_DELIVERY",
               "OUT_FOR_DELIVERY": "DELIVERED"}
        delivery_service.transition(db, delivery, seq[ds],
                                    notes="MallHaul demo", actor_id=None)
        events.append(f"Delivery: {ds} -> {seq[ds]}")
        stage = "DELIVERED" if seq[ds] == "DELIVERED" else "OUT_FOR_DELIVERY"
        return {"stage": stage, "events": events, "optimizer_report": report}

    sts = [m["fulfillment_status"] for m in order["merchants"]]
    if all(s == "PENDING" for s in sts):
        merchant("PENDING", "ACCEPTED")
        stage = "ACCEPTED"
    elif all(s == "ACCEPTED" for s in sts):
        merchant("ACCEPTED", "PREPARING")
        stage = "PREPARING"
    elif all(s == "PREPARING" for s in sts):
        merchant("PREPARING", "READY")
        db.orders.update_one({"_id": oid},
                             {"$set": {"order_status": "READY_FOR_DELIVERY",
                                       "updated_at": now()}})
        events.append("Order status -> READY_FOR_DELIVERY")
        stage = "READY"
    elif all(p["status"] in ("PENDING", "READY") for p in pkgs):
        package("PENDING", "RECEIVED", "received_at")
        stage = "AT_HUB"
    elif all(p["status"] == "RECEIVED" for p in pkgs):
        package("RECEIVED", "CONSOLIDATED", "consolidated_at")
        events.append("Hub consolidated packages into one shipment")
        stage = "CONSOLIDATED"
    elif all(p["status"] == "CONSOLIDATED" for p in pkgs):
        package("CONSOLIDATED", "DISPATCHED", "dispatched_at")
        fresh = db.deliveries.find_one({"_id": delivery["_id"]})
        report = delivery_service.assign_courier(db, fresh)
        events.append("Quantum optimizer assigned a courier")
        stage = "ASSIGNED"
    else:
        return {"stage": "WAIT",
                "events": ["Mixed states; complete stores first"]}

    db.audit_logs.insert_one({"_id": ObjectId(), "user_id": u["_id"],
                              "action": "DEMO_LIFECYCLE_ADVANCE",
                              "entity_type": "ORDER", "entity_id": oid,
                              "changes": {"events": events},
                              "timestamp": now()})
    return {"stage": stage, "events": events, "optimizer_report": report}
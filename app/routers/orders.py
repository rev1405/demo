# [DB CONNECTION] collections: orders, payments, payment_splits, refunds,
# deliveries, delivery_tracking, packages, qr_codes, wallets, wallet_transactions
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.dependencies import get_customer_doc
from app.services import order_service, wallet_service
from app.utils import clean

router = APIRouter(prefix="/api/orders", tags=["orders"])
now = lambda: datetime.now(timezone.utc)
CANCELLABLE = {"PENDING", "PROCESSING", "PARTIALLY_READY", "READY_FOR_DELIVERY"}


def _stage(order, delivery_status):
    if order["order_status"] == "DELIVERED":
        return 3
    if delivery_status in ("ASSIGNED", "PICKED_UP", "OUT_FOR_DELIVERY"):
        return 2
    if any(m["fulfillment_status"] != "PENDING" for m in order["merchants"]):
        return 1
    return 0


@router.get("")
def my_orders(c: dict = Depends(get_customer_doc)):
    db = get_db()
    orders = list(db.orders.find({"customer_id": c["_id"]})
                  .sort("created_at", -1).limit(50))
    oids = [o["_id"] for o in orders]
    dmap = {d["order_id"]: d for d in db.deliveries.find({"order_id": {"$in": oids}})}
    qmap = {q["entity_id"]: q["code"] for q in
            db.qr_codes.find({"entity_type": "ORDER",
                              "entity_id": {"$in": oids}})}
    out = []
    for o in orders:
        d = dmap.get(o["_id"])
        out.append({"_id": o["_id"], "order_number": o["order_number"],
                    "created_at": o["created_at"],
                    "store_count": len(o["merchants"]),
                    "item_count": sum(len(m["items"]) for m in o["merchants"]),
                    "total": o["pricing"]["total"],
                    "payment_status": o["payment_status"],
                    "order_status": o["order_status"],
                    "delivery_status": d["status"] if d else None,
                    "eta": d.get("estimated_delivery_time") if d else None,
                    "stage": _stage(o, d["status"] if d else None),
                    "master_qr": qmap.get(o["_id"])})
    return clean(out)


@router.get("/{order_id}")
def order_detail(order_id: str, c: dict = Depends(get_customer_doc)):
    db = get_db()
    try:
        oid = ObjectId(order_id)
    except Exception:
        raise HTTPException(400, "Invalid order id")
    order = db.orders.find_one({"_id": oid, "customer_id": c["_id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    packages = list(db.packages.find({"order_id": oid}))
    pids = [p["_id"] for p in packages]
    pkg_qr = {q["entity_id"]: q["code"] for q in
              db.qr_codes.find({"entity_type": "PACKAGE",
                                "entity_id": {"$in": pids}})}
    for p in packages:
        p["qr_code"] = pkg_qr.get(p["_id"])
    delivery = db.deliveries.find_one({"order_id": oid})
    tracking = (list(db.delivery_tracking.find({"delivery_id": delivery["_id"]})
                     .sort("timestamp", 1)) if delivery else [])
    master = db.qr_codes.find_one({"entity_type": "ORDER", "entity_id": oid})
    return clean({"order": order, "packages": packages,
                  "delivery": delivery, "tracking": tracking,
                  "master_qr": master["code"] if master else None,
                  "stage": _stage(order, delivery["status"] if delivery else None),
                  "cancellable": order["order_status"] in CANCELLABLE})


@router.post("/{order_id}/cancel")
def cancel(order_id: str, c: dict = Depends(get_customer_doc)):
    db = get_db()
    oid = ObjectId(order_id)
    order = db.orders.find_one({"_id": oid, "customer_id": c["_id"]})
    if not order:
        raise HTTPException(404, "Order not found")
    order_service.cancel_order(db, oid)     # tx: cancel + release stock + refund doc
    pay = db.payments.find_one({"order_id": oid, "status": "SUCCESS"})
    if pay:
        refund = db.refunds.find_one({"order_id": oid},
                                     sort=[("created_at", -1)])
        # tx: settle refund into the wallet (simulated PSP payout)
        wallet_service.refund(db, c["user_id"], pay["amount"], oid,
                              refund["_id"] if refund else None)
        if refund:
            db.refunds.update_one(
                {"_id": refund["_id"]},
                {"$set": {"status": "PROCESSED", "provider_refund_id": "WALLET",
                          "updated_at": now()}})
        db.payment_splits.update_many({"payment_id": pay["_id"]},
                                      {"$set": {"status": "REFUNDED",
                                                "updated_at": now()}})
        db.orders.update_one({"_id": oid},
                             {"$set": {"payment_status": "REFUNDED",
                                       "updated_at": now()}})
    return {"ok": True, "order_status": "CANCELLED"}
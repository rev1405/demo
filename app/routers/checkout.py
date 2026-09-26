# [DB CONNECTION] collections: carts, orders, payments, addresses, customers,
# wallets, wallet_transactions, payment_splits, packages, deliveries, qr_codes,
# notifications, audit_logs (via the services below).
# Orchestrates: checkout_service (tx 1) -> wallet charge (tx 2) ->
# payment_service.mark_payment_paid (tx 3) -> fulfillment_service (tx 4).
import uuid
from datetime import datetime, timezone

from bson import ObjectId
from bson.decimal128 import Decimal128
from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.dependencies import get_customer_doc, rate_limit
from app.schemas import CheckoutIn
from app.services import (checkout_service, delivery_service, fulfillment_service,
                          order_service, payment_service, wallet_service)
from app.utils import clean, to_float

router = APIRouter(prefix="/api", tags=["checkout"])
D = lambda v: Decimal128(str(v))
now = lambda: datetime.now(timezone.utc)
DELIVERY_FEES = {"BASE": 35.00, "DOOR_TO_DOOR": 55.00}


@router.post("/checkout")
def checkout(data: CheckoutIn, c: dict = Depends(get_customer_doc),
             _rl: None = Depends(rate_limit(limit=12))):
    db = get_db()
    cart = db.carts.find_one({"customer_id": c["_id"], "status": "ACTIVE"})
    if not cart or not cart["items"]:
        raise HTTPException(400, "Your trolley is empty")

    subtotal = round(sum(to_float(i["unit_price"]) * i["quantity"]
                         for i in cart["items"]), 2)
    delivery_fee = DELIVERY_FEES[data.delivery_option]
    platform_fee = round(subtotal * 0.03, 2)

    a = data.address
    location = None
    if a.latitude is not None and a.longitude is not None:
        location = {"type": "Point", "coordinates": [a.longitude, a.latitude]}
    address_snapshot = {"address_line_1": a.address_line_1.strip(),
                        "address_line_2": a.address_line_2,
                        "city": a.city.strip(), "province": a.province.strip(),
                        "postal_code": a.postal_code, "location": location}
    if data.save_address:
        aid = ObjectId()
        db.addresses.insert_one({"_id": aid, "user_id": c["user_id"],
                                 "label": None, **address_snapshot,
                                 "is_default": False,
                                 "created_at": now(), "updated_at": now()})
        db.customers.update_one({"_id": c["_id"]},
                                {"$set": {"default_address_id": aid}})

    # ---- TX 1: validate, reserve inventory, create order + PENDING payment ----
    order = checkout_service.checkout(
        db, c["_id"], data.idempotency_key, address_snapshot,
        D(delivery_fee), D(platform_fee), D("0"))

    payment = db.payments.find_one({"order_id": order["_id"]})
    try:
        # ---- TX 2: charge wallet (simulated PSP) ----
        wallet_service.charge(db, c["user_id"],
                              order["pricing"]["total"], order["_id"])
    except HTTPException:
        # Compensate: release stock and void the pending payment.
        order_service.cancel_order(db, order["_id"])
        db.payments.update_one({"_id": payment["_id"]},
                               {"$set": {"status": "CANCELLED",
                                         "updated_at": now()}})
        raise HTTPException(402, "Wallet balance too low. Top up and retry.")

    # ---- TX 3: payment SUCCESS + payment_splits (HELD) + order PROCESSING ----
    payment_service.mark_payment_paid(db, payment["_id"],
                                      f"WALLET-{uuid.uuid4().hex[:12]}")
    # ---- TX 4: packages, delivery, QR codes, notification ----
    fulfillment_service.create_fulfillment(db,
                                           db.orders.find_one({"_id": order["_id"]}))

    fresh = db.orders.find_one({"_id": order["_id"]})
    return clean({"order_id": fresh["_id"],
                  "order_number": fresh["order_number"],
                  "total": fresh["pricing"]["total"]})
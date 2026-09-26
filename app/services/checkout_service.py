"""UNIFIED CHECKOUT - one cart (multi-store) -> ONE order -> ONE payment.
[DB CONNECTION] collections: carts, mall_stores, mall_products, mall_inventory,
orders, payments, counters.

Transaction scope: validate cart -> validate stores/products -> atomically
reserve inventory -> create order (embedded per-store allocations) -> create
payment record. The wallet/PSP call happens AFTER commit, never inside.
"""
from datetime import datetime, timezone

from bson import ObjectId
from bson.decimal128 import Decimal128

from database.enums import FulfillmentStatus

from app.utils import to_float

D = lambda v: Decimal128(str(v))
now = lambda: datetime.now(timezone.utc)


class CheckoutError(Exception):
    pass


class OutOfStock(CheckoutError):
    pass


def _next_seq(db, key: str, session) -> int:
    from pymongo import ReturnDocument
    return db.counters.find_one_and_update(
        {"_id": key}, {"$inc": {"seq": 1}}, upsert=True,
        return_document=ReturnDocument.AFTER, session=session)["seq"]


def checkout(db, customer_id: ObjectId, idempotency_key: str,
             delivery_address: dict, delivery_fee, platform_fee_total,
             discount=None) -> dict:
    discount = discount or D("0")

    with db.client.start_session() as s:
        s.start_transaction()
        try:
            # 0) Idempotency - a replayed request returns the original order
            existing = db.payments.find_one(
                {"idempotency_key": idempotency_key}, session=s)
            if existing:
                s.abort_transaction()
                return db.orders.find_one({"_id": existing["order_id"]}, session=s)

            # 1) Validate cart (one ACTIVE cart guaranteed by partial unique index)
            cart = db.carts.find_one(
                {"customer_id": customer_id, "status": "ACTIVE"}, session=s)
            if not cart or not cart["items"]:
                raise CheckoutError("No active cart with items")

            # 2) Validate store in mall, product in store, refresh prices
            by_store: dict[ObjectId, dict] = {}
            for item in cart["items"]:
                store = db.mall_stores.find_one(
                    {"_id": item["store_id"], "mall_id": cart["mall_id"],
                     "is_active": True}, session=s)
                if not store:
                    raise CheckoutError("Store not in selected mall or inactive")
                prod = db.mall_products.find_one(
                    {"_id": item["product_id"], "store_id": item["store_id"],
                     "is_active": True}, session=s)
                if not prod:
                    raise CheckoutError(
                        f"Product unavailable: {item['product_name_snapshot']}")
                unit = to_float(prod["pricing"]["selling_price"])
                line = {
                    "product_id": prod["_id"],
                    "product_name_snapshot": prod["name"],      # historical snapshot
                    "sku_snapshot": prod.get("sku"),
                    "unit_price": D(unit),
                    "quantity": item["quantity"],
                    "total_price": D(round(unit * item["quantity"], 2)),
                }
                by_store.setdefault(item["store_id"], {"store": store, "items": []})
                by_store[item["store_id"]]["items"].append(line)

            # 3) ATOMIC RESERVATION: available = on_hand - reserved (guarded $inc)
            for sid, grp in by_store.items():
                for line in grp["items"]:
                    res = db.mall_inventory.update_one(
                        {"store_id": sid, "product_id": line["product_id"],
                         "$expr": {"$gte": [
                             {"$subtract": ["$quantity_on_hand",
                                            "$quantity_reserved"]},
                             line["quantity"]]}},
                        {"$inc": {"quantity_reserved": line["quantity"]},
                         "$set": {"updated_at": now()}},
                        session=s)
                    if res.modified_count == 0:
                        raise OutOfStock(line["product_name_snapshot"])

            # 4) Build the order aggregate - one allocation per store
            subtotal_f = sum(float(l["total_price"])
                             for g in by_store.values() for l in g["items"])
            merchants = []
            for sid, grp in by_store.items():
                store_sub = sum(float(l["total_price"]) for l in grp["items"])
                share = round(to_float(delivery_fee) * store_sub / subtotal_f, 2)
                fee = round(to_float(platform_fee_total) * store_sub / subtotal_f, 2)
                merchants.append({
                    "store_id": sid,
                    "store_name_snapshot": grp["store"]["name"],
                    "subtotal": D(store_sub),
                    "delivery_share": D(share),
                    "platform_fee": D(fee),
                    "merchant_amount": D(round(store_sub - share - fee, 2)),
                    "fulfillment_status": FulfillmentStatus.PENDING.value,
                    "items": grp["items"],
                })

            t = now()
            order_doc = {
                "_id": ObjectId(),
                "order_number": f"MH-{82802610 + _next_seq(db, 'order_number', s)}",
                "customer_id": customer_id,
                "mall_id": cart["mall_id"],
                "pricing": {
                    "subtotal": D(subtotal_f),
                    "delivery_fee": D(to_float(delivery_fee)),
                    "platform_fee": D(to_float(platform_fee_total)),
                    "discount": discount,
                    "total": D(round(subtotal_f + to_float(delivery_fee)
                                     + to_float(platform_fee_total)
                                     - to_float(discount), 2)),
                    "currency": "ZAR",
                },
                "delivery_address_snapshot": delivery_address,   # immutable snapshot
                "merchants": merchants,
                "payment_status": "PENDING_PAYMENT",
                "order_status": "PENDING",
                "created_at": t,
                "updated_at": t,
            }
            payment_doc = {
                "_id": ObjectId(),
                "order_id": order_doc["_id"],
                "customer_id": customer_id,
                "amount": order_doc["pricing"]["total"],
                "currency": "ZAR",
                "status": "PENDING",
                "payment_method": "MOBILE_WALLET",
                "provider": None,
                "provider_transaction_id": None,
                "idempotency_key": idempotency_key,
                "paid_at": None,
                "created_at": t,
                "updated_at": t,
            }

            db.orders.insert_one(order_doc, session=s)
            db.payments.insert_one(payment_doc, session=s)
            db.carts.update_one(
                {"_id": cart["_id"]},
                {"$set": {"status": "CONVERTED", "updated_at": t}}, session=s)

            s.commit_transaction()
            return order_doc
        except Exception:
            s.abort_transaction()   # reservations + cart flag roll back
            raise
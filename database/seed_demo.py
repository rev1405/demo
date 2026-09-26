"""MallHaul demo seed: Gateway / Rosebank / Canal Walk, 6 stores, products,
inventory, couriers, demo customer with wallet, one PROCESSING order and one
DELIVERED order. Idempotent: skips if Gateway already exists.
Run:  python -m database.seed_demo   (after migrations)"""
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from bson.decimal128 import Decimal128
from pymongo import ReturnDocument

from app.core.database import get_db
from app.core.security import hash_password

D = lambda v: Decimal128(str(v))
F = lambda x: float(x.to_decimal()) if isinstance(x, Decimal128) else float(x)
PT = lambda lng, lat: {"type": "Point", "coordinates": [lng, lat]}
NOW = datetime.now(timezone.utc)
H = lambda n: NOW + timedelta(hours=n)
DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY",
        "SUNDAY"]
db = get_db()


def next_seq(key):
    return db.counters.find_one_and_update(
        {"_id": key}, {"$inc": {"seq": 1}}, upsert=True,
        return_document=ReturnDocument.AFTER)["seq"]


def category(name):
    doc = db.categories.find_one({"name": name})
    if doc:
        return doc["_id"]
    cid = ObjectId()
    db.categories.insert_one({"_id": cid, "name": name, "description": None,
                              "is_active": True,
                              "created_at": NOW, "updated_at": NOW})
    return cid


def user(fn, ln, email, phone, roles, pw="Passw0rd!"):
    existing = db.users.find_one({"email": email})
    if existing:
        return existing["_id"]
    u = ObjectId()
    db.users.insert_one({"_id": u, "first_name": fn, "last_name": ln,
                         "email": email, "phone": phone,
                         "password_hash": hash_password(pw), "roles": roles,
                         "is_active": True, "created_at": NOW,
                         "updated_at": NOW})
    return u


if db.malls.find_one({"name": "Gateway Theatre of Shopping"}):
    print("Demo seed already present - nothing to do.")
    raise SystemExit

cats = {n: category(n) for n in
        ["Groceries", "Fashion", "Beauty", "Home", "Electronics"]}

u_demo = user("Demo", "Shopper", "demo@mallhaul.co.za", "+27821100077",
              ["CUSTOMER"], pw="Demo1234!")
u_r1 = user("Sanele", "Zwane", "sanele@example.com", "+27821100030", ["RUNNER"])
u_r2 = user("Lindiwe", "Ngema", "lindiwe@example.com", "+27821100031", ["RUNNER"])
u_d1 = user("Jabu", "Mahlangu", "jabu@example.com", "+27821100020", ["DRIVER"])
u_mgr = user("Lerato", "Dlamini", "pnp.gateway.manager@mallhaul.co.za",
             None, ["STORE_MANAGER"])

cust = db.customers.find_one({"user_id": u_demo})
if not cust:
    cid = ObjectId()
    db.customers.insert_one({"_id": cid, "user_id": u_demo,
                             "default_address_id": None,
                             "created_at": NOW, "updated_at": NOW})
    cust = {"_id": cid}
addr = ObjectId()
db.addresses.insert_one({"_id": addr, "user_id": u_demo, "label": "Home",
    "address_line_1": "22 Palm Boulevard", "address_line_2": None,
    "city": "Umhlanga", "province": "KwaZulu-Natal", "postal_code": "4319",
    "location": PT(31.0716, -29.7260), "is_default": True,
    "created_at": NOW, "updated_at": NOW})
db.customers.update_one({"_id": cust["_id"]},
                        {"$set": {"default_address_id": addr}})
if not db.wallets.find_one({"user_id": u_demo}):
    db.wallets.insert_one({"_id": ObjectId(), "user_id": u_demo,
                           "balance": D("1500.00"), "currency": "ZAR",
                           "created_at": NOW, "updated_at": NOW})
    db.wallet_transactions.insert_one({"_id": ObjectId(), "user_id": u_demo,
        "type": "TOPUP", "amount": D("1500.00"), "ref": "DEMO_GATEWAY",
        "order_id": None, "created_at": NOW})

d1 = ObjectId()
db.drivers.insert_one({"_id": d1, "user_id": u_d1, "vehicle_id": None,
    "status": "AVAILABLE", "current_location": PT(31.0680, -29.7270),
    "is_active": True, "created_at": NOW, "updated_at": NOW})
veh = ObjectId()
db.vehicles.insert_one({"_id": veh, "registration_number": "ND 123 456",
    "type": "CAR", "driver_id": d1, "is_active": True,
    "created_at": NOW, "updated_at": NOW})
db.drivers.update_one({"_id": d1}, {"$set": {"vehicle_id": veh}})
db.runners.insert_many([
    {"_id": ObjectId(), "user_id": u_r1, "status": "AVAILABLE",
     "current_location": PT(31.0690, -29.7255), "is_active": True,
     "created_at": NOW, "updated_at": NOW},
    {"_id": ObjectId(), "user_id": u_r2, "status": "AVAILABLE",
     "current_location": PT(18.5110, -33.8920), "is_active": True,
     "created_at": NOW, "updated_at": NOW}])


def mall(name, city, prov, l1, code, lng, lat, img, desc):
    m = ObjectId()
    db.malls.insert_one({"_id": m, "name": name, "description": desc,
        "address": {"address_line_1": l1, "city": city, "province": prov,
                    "postal_code": code},
        "location": PT(lng, lat),
        "contact": {"phone": None, "email": None},
        "operating_hours": [{"day": d, "open": "09:00", "close": "18:00"}
                            for d in DAYS],
        "image_url": img, "is_active": True,
        "created_at": NOW, "updated_at": NOW})
    h = ObjectId()
    db.fulfillment_hubs.insert_one({
        "_id": h, "mall_id": m, "name": f"{name.split()[0]} Fulfilment Hub",
        "location": PT(lng + 0.0008, lat - 0.0004), "is_active": True,
        "created_at": NOW, "updated_at": NOW})
    return m, h


U = "https://images.unsplash.com/photo-"
gateway, ghub = mall("Gateway Theatre of Shopping", "Umhlanga",
    "KwaZulu-Natal", "1 Palm Boulevard", "4319", 31.0696, -29.7253,
    U + "1481437156560-3205f6a55735?w=1100&auto=format&fit=crop&q=60",
    "KZN's largest super-regional shopping centre.")
rosebank, rhub = mall("Rosebank Mall", "Johannesburg", "Gauteng",
    "50 Bath Avenue, Rosebank", "2196", 28.0406, -26.1435,
    U + "1486406146926-c627a92ad1ab?w=1100&auto=format&fit=crop&q=60",
    "Sophisticated urban shopping in the heart of Rosebank.")
canal, chub = mall("Canal Walk", "Cape Town", "Western Cape",
    "Century Boulevard, Milnerton", "7441", 18.5102, -33.8917,
    U + "1555529669-e69e7aa0ba9a?w=1100&auto=format&fit=crop&q=60",
    "The Cape's premier retail and entertainment destination.")

STORES = [
 (gateway, "Pick n Pay Gateway", "Groceries",
  U + "1542838132-92c53300491e?w=800&auto=format&fit=crop&q=60",
  [("Rice 2kg", "RICE-2", 45.00, 80), ("Brown Bread 750g", "BRD-750", 18.99, 100),
   ("Full Cream Milk 2L", "MLK-2", 32.99, 70), ("Large Eggs 30s", "EGG-30", 54.99, 45),
   ("Rooibos Tea 80s", "TEA-80", 42.99, 50)]),
 (gateway, "Mr Price Gateway", "Fashion",
  U + "1441986300917-64674bd600d8?w=800&auto=format&fit=crop&q=60",
  [("Graphic Tee", "MPT-1", 119.00, 55), ("Hoodie", "MPH-2", 299.00, 30),
   ("Beanie", "MPB-3", 59.00, 60), ("Cap", "MPC-4", 99.00, 40),
   ("Socks 3-pack", "MPS-5", 69.00, 80)]),
 (rosebank, "Clicks Rosebank", "Beauty",
  U + "1522335789203-aabd1fc54bc9?w=800&auto=format&fit=crop&q=60",
  [("Sunscreen SPF50", "CLK-S1", 129.99, 40), ("Body Lotion 400ml", "CLK-L2", 64.99, 60),
   ("Lip Balm", "CLK-B3", 29.99, 90), ("Multivitamins", "CLK-M4", 99.99, 35)]),
 (rosebank, "Typo Rosebank", "Home",
  U + "1524995997946-a1c2e315a42f?w=800&auto=format&fit=crop&q=60",
  [("Desk Lamp", "TYP-1", 249.00, 20), ("Notebook A5", "TYP-2", 59.00, 90),
   ("Scented Candle", "TYP-3", 149.00, 35), ("Photo Frames 3pk", "TYP-4", 129.00, 28)]),
 (canal, "Game Canal", "Electronics",
  U + "1518770660439-4636190af475?w=800&auto=format&fit=crop&q=60",
  [("Wireless Earbuds", "GM-1", 499.00, 25), ("Power Bank 20000mAh", "GM-2", 349.00, 30),
   ("USB-C Cable 1m", "GM-3", 79.00, 120), ("Smart Watch", "GM-4", 1299.00, 12)]),
 (canal, "Woolworths Canal", "Fashion",
  U + "1483985988355-763728e1935b?w=800&auto=format&fit=crop&q=60",
  [("Men's Chinos", "WOW-1", 399.00, 22), ("Ladies Scarf", "WOW-2", 199.00, 30),
   ("Kids Tee", "WOW-3", 89.00, 60), ("Leather Belt", "WOW-4", 249.00, 18)]),
]
store_ids, product_index = {}, {}
for mall_id, sname, catname, img, products in STORES:
    sid = ObjectId()
    store_ids[sname] = sid
    db.mall_stores.insert_one({"_id": sid, "mall_id": mall_id, "name": sname,
        "description": f"{catname} store", "store_number": None,
        "category_id": cats[catname],
        "address": {"floor": None, "unit": None},
        "contact": {"phone": None, "email": None},
        "operating_hours": [], "image_url": img, "is_active": True,
        "created_at": NOW, "updated_at": NOW})
    db.mall_store_staff.insert_one({"_id": ObjectId(), "store_id": sid,
        "user_id": u_mgr, "role": "STORE_MANAGER", "is_active": True,
        "created_at": NOW, "updated_at": NOW})
    for pname, sku, price, qty in products:
        p = ObjectId()
        product_index[(sname, sku)] = (p, price, pname)
        db.mall_products.insert_one({"_id": p, "store_id": sid, "name": pname,
            "description": None, "sku": sku, "category_id": cats[catname],
            "images": [],
            "pricing": {"selling_price": D(price), "currency": "ZAR"},
            "unit_type": "EACH", "is_active": True,
            "created_at": NOW, "updated_at": NOW})
        db.mall_inventory.insert_one({"_id": ObjectId(), "product_id": p,
            "store_id": sid, "quantity_on_hand": qty, "quantity_reserved": 0,
            "reorder_level": max(5, qty // 10), "updated_at": NOW})


def mk_order(items, mall_id, hub_id, delivered=False):
    """Complete order aggregate with payment, splits, packages, delivery, QRs."""
    by_store = {}
    for sname, sku, qty in items:
        pid, price, pname = product_index[(sname, sku)]
        by_store.setdefault(sname, []).append(
            {"product_id": pid, "product_name_snapshot": pname,
             "sku_snapshot": sku, "unit_price": D(price), "quantity": qty,
             "total_price": D(round(price * qty, 2))})
    subtotal = round(sum(F(i["total_price"])
                         for l in by_store.values() for i in l), 2)
    fee = round(subtotal * 0.03, 2)
    total = round(subtotal + 35.00 + fee, 2)
    merchants = []
    for sname, lines in by_store.items():
        ssub = round(sum(F(i["total_price"]) for i in lines), 2)
        share = round(35.00 * ssub / subtotal, 2)
        sfee = round(fee * ssub / subtotal, 2)
        merchants.append({"store_id": store_ids[sname],
                          "store_name_snapshot": sname,
                          "subtotal": D(ssub), "delivery_share": D(share),
                          "platform_fee": D(sfee),
                          "merchant_amount": D(round(ssub - share - sfee, 2)),
                          "fulfillment_status":
                              "COMPLETED" if delivered else "PENDING",
                          "items": lines})
    oid = ObjectId()
    created = H(-30) if delivered else H(-2)
    db.orders.insert_one({"_id": oid,
        "order_number": f"MH-{82802610 + next_seq('order_number')}",
        "customer_id": cust["_id"], "mall_id": mall_id,
        "pricing": {"subtotal": D(subtotal), "delivery_fee": D("35.00"),
                    "platform_fee": D(fee), "discount": D("0"),
                    "total": D(total), "currency": "ZAR"},
        "delivery_address_snapshot": {"address_line_1": "22 Palm Boulevard",
            "address_line_2": None, "city": "Umhlanga",
            "province": "KwaZulu-Natal", "postal_code": "4319",
            "location": PT(31.0716, -29.7260)},
        "merchants": merchants,
        "payment_status": "PAID",
        "order_status": "DELIVERED" if delivered else "PROCESSING",
        "created_at": created, "updated_at": H(-24) if delivered else H(-1)})
    pay = ObjectId()
    db.payments.insert_one({"_id": pay, "order_id": oid,
        "customer_id": cust["_id"], "amount": D(total), "currency": "ZAR",
        "status": "SUCCESS", "payment_method": "MOBILE_WALLET",
        "provider": "DEMO", "provider_transaction_id": f"DEMO-{str(oid)[-12:]}",
        "idempotency_key": f"seed-{str(oid)[-12:]}",
        "paid_at": created, "created_at": created,
        "updated_at": H(-24) if delivered else created})
    for m in merchants:
        db.payment_splits.insert_one({"_id": ObjectId(), "payment_id": pay,
            "order_id": oid, "store_id": m["store_id"],
            "gross_amount": m["merchant_amount"],
            "platform_fee": m["platform_fee"],
            "net_amount": D(F(m["merchant_amount"])
                            - F(m["platform_fee"])),
            "status": "RELEASED" if delivered else "HELD",
            "released_at": H(-24) if delivered else None,
            "created_at": NOW, "updated_at": NOW})
    did = ObjectId()
    db.deliveries.insert_one({"_id": did, "order_id": oid,
        "driver_id": None, "runner_id": None, "vehicle_id": None,
        "pickup": PT(31.0704, -29.7257), "dropoff": PT(31.0716, -29.7260),
        "status": "DELIVERED" if delivered else "PENDING",
        "estimated_delivery_time": H(-24) if delivered else None,
        "created_at": NOW, "updated_at": NOW})
    db.qr_codes.insert_one({"_id": ObjectId(), "entity_type": "ORDER",
        "entity_id": oid, "code": f"MH-QR-{str(oid)[-12:]}",
        "status": "SCANNED" if delivered else "ACTIVE", "expires_at": None,
        "scanned_at": H(-24) if delivered else None, "created_at": NOW})
    for m in merchants:
        pkg = ObjectId()
        db.packages.insert_one({"_id": pkg, "order_id": oid,
            "store_id": m["store_id"],
            "package_number": f"PKG-{next_seq('package_number'):04d}",
            "items": [{"product_id": i["product_id"], "quantity": i["quantity"]}
                      for i in m["items"]],
            "status": "DISPATCHED" if delivered else "PENDING",
            "fulfillment_hub_id": hub_id,
            "received_at": H(-29) if delivered else None,
            "consolidated_at": H(-28) if delivered else None,
            "dispatched_at": H(-27) if delivered else None,
            "created_at": NOW, "updated_at": NOW})
        db.qr_codes.insert_one({"_id": ObjectId(), "entity_type": "PACKAGE",
            "entity_id": pkg, "code": f"MH-QR-{str(pkg)[-12:]}",
            "status": "SCANNED" if delivered else "ACTIVE", "expires_at": None,
            "scanned_at": H(-27) if delivered else None, "created_at": NOW})
    if delivered:
        for ev, hrs in [("ASSIGNED", 28), ("PICKED_UP", 27.5), ("AT_HUB", 27.2),
                        ("OUT_FOR_DELIVERY", 27), ("DRIVER_ARRIVED", 24.5),
                        ("DELIVERED", 24)]:
            db.delivery_tracking.insert_one({"_id": ObjectId(),
                "delivery_id": did, "status": ev, "location": None,
                "notes": None, "timestamp": H(-hrs)})
    db.notifications.insert_one({"_id": ObjectId(), "user_id": u_demo,
        "type": "ORDER_STATUS", "title": "Order confirmed",
        "message": f"Order {str(oid)[-6:]} confirmed.",
        "reference": {"entity_type": "ORDER", "entity_id": oid},
        "is_read": False, "read_at": None, "created_at": NOW})
    return oid


# in-progress order for the Demo page (two stores at Gateway)
mk_order([("Pick n Pay Gateway", "RICE-2", 1),
          ("Pick n Pay Gateway", "BRD-750", 2),
          ("Mr Price Gateway", "MPB-3", 1)], gateway, ghub)
# historical delivered order at Rosebank
mk_order([("Clicks Rosebank", "CLK-B3", 2),
          ("Typo Rosebank", "TYP-2", 1)], rosebank, rhub, delivered=True)

print("MallHaul demo seed complete. Login: demo@mallhaul.co.za / Demo1234!")
# [DB CONNECTION] collections: carts, mall_products, mall_stores, malls
from datetime import datetime, timezone

from bson import ObjectId
from bson.decimal128 import Decimal128
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.core.database import get_db
from app.dependencies import get_customer_doc
from app.schemas import CartAddIn, CartQtyIn
from app.utils import clean, to_float

router = APIRouter(prefix="/api/cart", tags=["cart"])
D = lambda v: Decimal128(str(v))
now = lambda: datetime.now(timezone.utc)
BASE_DELIVERY = D("35.00")


def _active_cart(db, customer_id):
    return db.carts.find_one({"customer_id": customer_id, "status": "ACTIVE"})


def _recalc(db, cart_id):
    cart = db.carts.find_one({"_id": cart_id})
    sub = round(sum(to_float(i["unit_price"]) * i["quantity"]
                    for i in cart["items"]), 2)
    db.carts.update_one({"_id": cart_id},
                        {"$set": {"subtotal": D(sub), "delivery_fee": BASE_DELIVERY,
                                  "total": D(round(sub + 35.0, 2)),
                                  "updated_at": now()}})
    return db.carts.find_one({"_id": cart_id})


def _with_names(db, cart):
    ids = list({i["store_id"] for i in cart.get("items", [])})
    names = {s["_id"]: s["name"] for s in db.mall_stores.find({"_id": {"$in": ids}})}
    for i in cart.get("items", []):
        i["store_name"] = names.get(i["store_id"], "Store")
    return cart


@router.get("")
def get_cart(c: dict = Depends(get_customer_doc)):
    db = get_db()
    cart = _active_cart(db, c["_id"]) or {
        "_id": None, "mall_id": None, "items": [], "subtotal": D("0"),
        "delivery_fee": BASE_DELIVERY, "total": D("0")}
    return clean(_with_names(db, cart))


@router.post("/items", status_code=201)
def add_item(data: CartAddIn, c: dict = Depends(get_customer_doc)):
    db = get_db()
    try:
        pid = ObjectId(data.product_id)
    except InvalidId:
        raise HTTPException(400, "Invalid product id")
    product = db.mall_products.find_one({"_id": pid, "is_active": True})
    if not product:
        raise HTTPException(404, "Product unavailable")
    store = db.mall_stores.find_one({"_id": product["store_id"], "is_active": True})
    mall = (db.malls.find_one({"_id": store["mall_id"], "is_active": True})
            if store else None)
    if not store or not mall:
        raise HTTPException(409, "Store or mall unavailable")

    cart = _active_cart(db, c["_id"])
    if cart and cart["mall_id"] != mall["_id"]:
        # One trolley per customer, scoped to one mall (business rule).
        mall_name = db.malls.find_one({"_id": cart["mall_id"]})["name"]
        raise HTTPException(409, detail={
            "code": "MALL_CONFLICT",
            "message": f"Your trolley is for {mall_name}. Clear it to shop this mall."})

    if not cart:
        try:
            db.carts.insert_one({
                "_id": ObjectId(), "customer_id": c["_id"], "mall_id": mall["_id"],
                "status": "ACTIVE", "items": [], "subtotal": D("0"),
                "delivery_fee": BASE_DELIVERY, "total": D("0"),
                "created_at": now(), "updated_at": now()})
        except DuplicateKeyError:      # race on the one-active-cart index
            pass
        cart = _active_cart(db, c["_id"])

    unit = to_float(product["pricing"]["selling_price"])
    existing = db.carts.find_one({"_id": cart["_id"], "items.product_id": pid})
    if existing:
        item = next(i for i in existing["items"] if i["product_id"] == pid)
        new_qty = min(99, item["quantity"] + data.quantity)
        db.carts.update_one({"_id": cart["_id"], "items._id": item["_id"]},
                            {"$set": {"items.$.quantity": new_qty,
                                      "items.$.total_price": D(round(unit * new_qty, 2)),
                                      "updated_at": now()}})
    else:
        new_item = {"_id": ObjectId(), "product_id": pid, "store_id": store["_id"],
                    "product_name_snapshot": product["name"],
                    "sku_snapshot": product.get("sku"), "unit_price": D(unit),
                    "quantity": data.quantity,
                    "total_price": D(round(unit * data.quantity, 2))}
        db.carts.update_one({"_id": cart["_id"]},
                            {"$push": {"items": new_item},
                             "$set": {"updated_at": now()}})
    return clean(_with_names(db, _recalc(db, cart["_id"])))


@router.patch("/items/{item_id}")
def set_qty(item_id: str, data: CartQtyIn, c: dict = Depends(get_customer_doc)):
    db = get_db()
    cart = _active_cart(db, c["_id"])
    if not cart:
        raise HTTPException(404, "No active trolley")
    try:
        iid = ObjectId(item_id)
    except InvalidId:
        raise HTTPException(400, "Invalid item id")
    item = next((i for i in cart["items"] if i["_id"] == iid), None)
    if not item:
        raise HTTPException(404, "Item not in trolley")
    if data.quantity == 0:
        db.carts.update_one({"_id": cart["_id"]},
                            {"$pull": {"items": {"_id": iid}},
                             "$set": {"updated_at": now()}})
    else:
        unit = to_float(item["unit_price"])
        db.carts.update_one({"_id": cart["_id"], "items._id": iid},
                            {"$set": {"items.$.quantity": data.quantity,
                                      "items.$.total_price":
                                          D(round(unit * data.quantity, 2)),
                                      "updated_at": now()}})
    return clean(_with_names(db, _recalc(db, cart["_id"])))


@router.delete("/items/{item_id}")
def remove_item(item_id: str, c: dict = Depends(get_customer_doc)):
    db = get_db()
    cart = _active_cart(db, c["_id"])
    if not cart:
        raise HTTPException(404, "No active trolley")
    db.carts.update_one({"_id": cart["_id"]},
                        {"$pull": {"items": {"_id": ObjectId(item_id)}},
                         "$set": {"updated_at": now()}})
    return clean(_with_names(db, _recalc(db, cart["_id"])))


@router.delete("")
def clear_cart(c: dict = Depends(get_customer_doc)):
    db = get_db()
    cart = _active_cart(db, c["_id"])
    if cart:
        db.carts.update_one({"_id": cart["_id"]},
                            {"$set": {"items": [], "subtotal": D("0"),
                                      "total": D("0"), "updated_at": now()}})
    return {"ok": True}
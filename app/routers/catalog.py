# [DB CONNECTION] collections: malls, mall_stores, categories, mall_products, mall_inventory
import re

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from app.core.database import get_db
from app.utils import clean

router = APIRouter(prefix="/api", tags=["catalog"])


@router.get("/malls")
def list_malls(q: str | None = None):
    db = get_db()
    flt: dict = {"is_active": True}
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}   # escaped: no regex injection
        flt["$or"] = [{"name": rx}, {"address.city": rx}]
    malls = list(db.malls.find(flt))
    counts = {c["_id"]: c["n"] for c in db.mall_stores.aggregate([
        {"$match": {"is_active": True}},
        {"$group": {"_id": "$mall_id", "n": {"$sum": 1}}}])}
    for m in malls:
        m["store_count"] = counts.get(m["_id"], 0)
    return clean(malls)


@router.get("/malls/{mall_id}")
def mall_detail(mall_id: str):
    db = get_db()
    mall = db.malls.find_one({"_id": ObjectId(mall_id), "is_active": True})
    if not mall:
        raise HTTPException(404, "Mall not found")
    stores = list(db.mall_stores.find({"mall_id": mall["_id"], "is_active": True}))
    cat_ids = [s["category_id"] for s in stores if s.get("category_id")]
    cats = {c["_id"]: c["name"] for c in db.categories.find({"_id": {"$in": cat_ids}})}
    ids = [s["_id"] for s in stores]
    prod_counts = {c["_id"]: c["n"] for c in db.mall_products.aggregate([
        {"$match": {"store_id": {"$in": ids}, "is_active": True}},
        {"$group": {"_id": "$store_id", "n": {"$sum": 1}}}])}
    for s in stores:
        s["category_name"] = cats.get(s.get("category_id"), "Other")
        s["product_count"] = prod_counts.get(s["_id"], 0)
    mall["stores"] = stores
    return clean(mall)


@router.get("/categories")
def categories():
    return clean(list(get_db().categories.find({"is_active": True})))


@router.get("/stores/{store_id}/products")
def store_products(store_id: str):
    db = get_db()
    store = db.mall_stores.find_one({"_id": ObjectId(store_id), "is_active": True})
    if not store:
        raise HTTPException(404, "Store not found")
    products = list(db.mall_products.find({"store_id": store["_id"],
                                           "is_active": True}))
    inv = {i["product_id"]: i for i in db.mall_inventory.find(
        {"product_id": {"$in": [p["_id"] for p in products]}})}
    for p in products:
        i = inv.get(p["_id"], {})
        p["available"] = max(0, i.get("quantity_on_hand", 0)
                             - i.get("quantity_reserved", 0))
    return clean({"store": store, "products": products})
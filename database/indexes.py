"""All indexes: unique, partial-unique, compound, 2dsphere."""
from pymongo import ASCENDING as ASC, DESCENDING as DESC, IndexModel


def IX(keys, **kw):
    return IndexModel(keys, **kw)


INDEXES = {
    "users": [
        IX([("email", ASC)], unique=True, name="uq_users_email"),
        IX([("phone", ASC)], unique=True, name="uq_users_phone",
           partialFilterExpression={"phone": {"$type": "string"}}),
        IX([("roles", ASC)], name="ix_users_roles"),
    ],
    "customers": [IX([("user_id", ASC)], unique=True, name="uq_customers_user")],
    "addresses": [
        IX([("user_id", ASC)], name="ix_addresses_user"),
        IX([("location", "2dsphere")], name="geo_addresses_location"),
        IX([("user_id", ASC)], unique=True, name="uq_one_default_per_user",
           partialFilterExpression={"is_default": True}),
    ],
    "categories": [IX([("name", ASC)], unique=True, name="uq_categories_name")],
    "malls": [
        IX([("location", "2dsphere")], name="geo_malls_location"),
        IX([("name", ASC)], name="ix_malls_name"),
    ],
    "mall_stores": [
        IX([("mall_id", ASC), ("is_active", ASC)], name="ix_stores_mall_active"),
        IX([("category_id", ASC)], name="ix_stores_category"),
    ],
    "mall_store_staff": [
        IX([("store_id", ASC), ("user_id", ASC)], name="ix_staff_store_user")],
    "mall_products": [
        IX([("store_id", ASC), ("is_active", ASC), ("name", ASC)],
           name="ix_products_store_browse"),
        IX([("store_id", ASC), ("sku", ASC)], unique=True,
           name="uq_products_sku_per_store",
           partialFilterExpression={"sku": {"$type": "string"}}),
        IX([("category_id", ASC)], name="ix_products_category"),
    ],
    "mall_inventory": [
        IX([("store_id", ASC), ("product_id", ASC)], unique=True,
           name="uq_inventory_store_product"),
        IX([("product_id", ASC)], name="ix_inventory_product"),
        IX([("store_id", ASC)], name="ix_inventory_store"),
    ],
    "fulfillment_hubs": [IX([("mall_id", ASC)], name="ix_hubs_mall")],
    "packages": [
        IX([("order_id", ASC)], name="ix_packages_order"),
        IX([("order_id", ASC), ("store_id", ASC)], name="ix_packages_order_store"),
        IX([("fulfillment_hub_id", ASC), ("status", ASC)],
           name="ix_packages_hub_status"),
    ],
    "carts": [
        IX([("customer_id", ASC)], unique=True,
           name="uq_one_active_cart_per_customer",
           partialFilterExpression={"status": "ACTIVE"}),
        IX([("mall_id", ASC)], name="ix_carts_mall"),
    ],
    "orders": [
        IX([("order_number", ASC)], unique=True, name="uq_orders_number"),
        IX([("customer_id", ASC), ("created_at", DESC)],
           name="ix_orders_customer_recent"),
        IX([("mall_id", ASC), ("order_status", ASC), ("created_at", DESC)],
           name="ix_orders_mall_status"),
        IX([("merchants.store_id", ASC), ("merchants.fulfillment_status", ASC)],
           name="ix_orders_store_fulfillment"),
    ],
    "payments": [
        IX([("order_id", ASC)], name="ix_payments_order"),
        IX([("provider_transaction_id", ASC)], unique=True,
           name="uq_payments_provider_txn",
           partialFilterExpression={"provider_transaction_id":
                                    {"$type": "string"}}),
        IX([("idempotency_key", ASC)], unique=True,
           name="uq_payments_idempotency",
           partialFilterExpression={"idempotency_key": {"$type": "string"}}),
    ],
    "payment_splits": [
        IX([("payment_id", ASC)], name="ix_splits_payment"),
        IX([("order_id", ASC)], name="ix_splits_order"),
        IX([("store_id", ASC), ("status", ASC)], name="ix_splits_store_status"),
        IX([("payment_id", ASC), ("store_id", ASC)], unique=True,
           name="uq_split_per_store"),
    ],
    "refunds": [
        IX([("payment_id", ASC)], name="ix_refunds_payment"),
        IX([("order_id", ASC)], name="ix_refunds_order"),
    ],
    "deliveries": [
        IX([("order_id", ASC)], name="ix_deliveries_order"),
        IX([("driver_id", ASC), ("status", ASC)], name="ix_deliveries_driver"),
        IX([("runner_id", ASC), ("status", ASC)], name="ix_deliveries_runner"),
        IX([("pickup", "2dsphere")], name="geo_deliveries_pickup"),
        IX([("dropoff", "2dsphere")], name="geo_deliveries_dropoff"),
    ],
    "delivery_tracking": [
        IX([("delivery_id", ASC), ("timestamp", DESC)],
           name="ix_tracking_delivery_time")],
    "drivers": [
        IX([("user_id", ASC)], unique=True, name="uq_drivers_user"),
        IX([("current_location", "2dsphere")], name="geo_drivers_location"),
        IX([("status", ASC), ("is_active", ASC)], name="ix_drivers_available"),
    ],
    "runners": [
        IX([("user_id", ASC)], unique=True, name="uq_runners_user"),
        IX([("current_location", "2dsphere")], name="geo_runners_location"),
        IX([("status", ASC), ("is_active", ASC)], name="ix_runners_available"),
    ],
    "vehicles": [
        IX([("registration_number", ASC)], unique=True,
           name="uq_vehicles_registration"),
        IX([("driver_id", ASC)], unique=True,
           name="uq_one_active_vehicle_per_driver",
           partialFilterExpression={"is_active": True}),
    ],
    "qr_codes": [
        IX([("code", ASC)], unique=True, name="uq_qr_code"),
        IX([("entity_type", ASC), ("entity_id", ASC)], name="ix_qr_entity"),
    ],
    "notifications": [
        IX([("user_id", ASC), ("is_read", ASC), ("created_at", DESC)],
           name="ix_notifications_inbox")],
    "reviews": [
        IX([("store_id", ASC), ("created_at", DESC)], name="ix_reviews_store"),
        IX([("customer_id", ASC), ("created_at", DESC)],
           name="ix_reviews_customer"),
        IX([("order_id", ASC), ("store_id", ASC)], unique=True,
           name="uq_review_per_store_order"),
    ],
    "audit_logs": [
        IX([("entity_type", ASC), ("entity_id", ASC), ("timestamp", DESC)],
           name="ix_audit_entity"),
        IX([("user_id", ASC), ("timestamp", DESC)], name="ix_audit_user"),
    ],
    "wallets": [IX([("user_id", ASC)], unique=True, name="uq_wallet_user")],
    "wallet_transactions": [
        IX([("user_id", ASC), ("created_at", -1)], name="ix_wtx_user")],
}


def create_all(db):
    for coll, models in INDEXES.items():
        db[coll].create_indexes(models)
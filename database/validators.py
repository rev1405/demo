"""MongoDB $jsonSchema guardrails. Pydantic is the primary API validator;
this is the second line of defence at rest. [SSDLC: dual validation]
ASSUMPTION: money is Decimal128 - never floats."""
MONEY      = {"bsonType": "decimal"}
NULL_MONEY = {"bsonType": ["decimal", "null"]}
STR        = {"bsonType": "string"}
NULL_STR   = {"bsonType": ["string", "null"]}
OID        = {"bsonType": "objectId"}
NULL_OID   = {"bsonType": ["objectId", "null"]}
DATE       = {"bsonType": "date"}
NULL_DATE  = {"bsonType": ["date", "null"]}
BOOL       = {"bsonType": "bool"}
INT        = {"bsonType": "number", "minimum": 0}
GEO = {"bsonType": "object", "required": ["type", "coordinates"],
       "properties": {"type": {"enum": ["Point"]},
                      "coordinates": {"bsonType": "array", "minItems": 2,
                                      "maxItems": 2,
                                      "items": {"bsonType": "number"}}}}
GEO_NULL = {"bsonType": ["object", "null"], "required": GEO["required"], "properties": GEO["properties"]}


def schema(required, props):
    return {"$jsonSchema": {"bsonType": "object",
                            "required": required, "properties": props}}


TS      = {"created_at": DATE, "updated_at": DATE}
CONTACT = {"bsonType": "object", "properties": {"phone": NULL_STR, "email": NULL_STR}}
OP_HOUR = {"bsonType": "object", "required": ["day"],
           "properties": {"day": {"enum": ["MONDAY", "TUESDAY", "WEDNESDAY",
                                           "THURSDAY", "FRIDAY", "SATURDAY",
                                           "SUNDAY"]},
                          "open": NULL_STR, "close": NULL_STR}}
ADDR_SNAPSHOT = {"bsonType": "object",
                 "required": ["address_line_1", "city", "province"],
                 "properties": {"address_line_1": STR, "address_line_2": NULL_STR,
                                "city": STR, "province": STR,
                                "postal_code": NULL_STR, "location": GEO_NULL}}
ORDER_ITEM = {"bsonType": "object",
              "required": ["product_id", "product_name_snapshot", "unit_price",
                           "quantity", "total_price"],
              "properties": {"product_id": OID, "product_name_snapshot": STR,
                             "sku_snapshot": NULL_STR, "unit_price": MONEY,
                             "quantity": {"bsonType": "number", "minimum": 1},
                             "total_price": MONEY}}
MERCHANT_ALLOC = {"bsonType": "object",
                  "required": ["store_id", "store_name_snapshot", "subtotal",
                               "delivery_share", "platform_fee",
                               "merchant_amount", "fulfillment_status", "items"],
                  "properties": {
                      "store_id": OID, "store_name_snapshot": STR,
                      "subtotal": MONEY, "delivery_share": MONEY,
                      "platform_fee": MONEY, "merchant_amount": MONEY,
                      "fulfillment_status": {"enum": ["PENDING", "ACCEPTED",
                                                      "PREPARING", "READY",
                                                      "HANDED_TO_DRIVER",
                                                      "COMPLETED", "CANCELLED"]},
                      "items": {"bsonType": "array", "minItems": 1,
                                "items": ORDER_ITEM}}}

VALIDATORS = {
    "users": schema(["first_name", "email", "roles", "is_active"], {
        "first_name": STR, "last_name": NULL_STR, "email": STR, "phone": NULL_STR,
        "password_hash": NULL_STR,                       # NEVER plaintext
        "roles": {"bsonType": "array", "minItems": 1, "items": {"enum": [
            "CUSTOMER", "MALL_ADMIN", "STORE_MANAGER", "STORE_STAFF",
            "FULFILLMENT_STAFF", "DRIVER", "RUNNER", "SYSTEM_ADMIN"]}},
        "is_active": BOOL, "last_login_at": NULL_DATE, **TS}),

    "customers": schema(["user_id"], {
        "user_id": OID, "default_address_id": NULL_OID, **TS}),

    "addresses": schema(["user_id", "address_line_1", "city", "province",
                         "location"], {
        "user_id": OID, "label": NULL_STR, "address_line_1": STR,
        "address_line_2": NULL_STR, "city": STR, "province": STR,
        "postal_code": NULL_STR, "location": GEO, "is_default": BOOL, **TS}),

    "categories": schema(["name", "is_active"], {
        "name": STR, "description": NULL_STR, "is_active": BOOL, **TS}),

    "malls": schema(["name", "address", "location", "is_active"], {
        "name": STR, "description": NULL_STR,
        "address": {"bsonType": "object",
                    "required": ["address_line_1", "city", "province"],
                    "properties": {"address_line_1": STR, "city": STR,
                                   "province": STR, "postal_code": NULL_STR}},
        "location": GEO, "contact": CONTACT,
        "operating_hours": {"bsonType": "array", "items": OP_HOUR},
        "image_url": NULL_STR, "is_active": BOOL, **TS}),

    "mall_stores": schema(["mall_id", "name", "is_active"], {
        "mall_id": OID, "name": STR, "description": NULL_STR,
        "store_number": NULL_STR, "category_id": NULL_OID,
        "address": {"bsonType": "object",
                    "properties": {"floor": NULL_STR, "unit": NULL_STR}},
        "contact": CONTACT,
        "operating_hours": {"bsonType": "array", "items": OP_HOUR},
        "image_url": NULL_STR, "is_active": BOOL, **TS}),

    "mall_store_staff": schema(["store_id", "user_id", "role", "is_active"], {
        "store_id": OID, "user_id": OID,
        "role": {"enum": ["STORE_MANAGER", "STORE_STAFF"]},
        "is_active": BOOL, **TS}),

    "mall_products": schema(["store_id", "name", "pricing", "is_active"], {
        "store_id": OID, "name": STR, "description": NULL_STR, "sku": NULL_STR,
        "category_id": NULL_OID, "images": {"bsonType": "array", "items": STR},
        "pricing": {"bsonType": "object",
                    "required": ["selling_price", "currency"],
                    "properties": {"selling_price": MONEY, "currency": STR}},
        "unit_type": NULL_STR, "is_active": BOOL, **TS}),

    "mall_inventory": schema(
        ["product_id", "store_id", "quantity_on_hand", "quantity_reserved",
         "reorder_level"], {
            "product_id": OID, "store_id": OID,
            "quantity_on_hand": INT, "quantity_reserved": INT,
            "reorder_level": INT, "updated_at": DATE}),

    "fulfillment_hubs": schema(["mall_id", "name", "location", "is_active"], {
        "mall_id": OID, "name": STR, "location": GEO, "is_active": BOOL, **TS}),

    "packages": schema(["order_id", "store_id", "package_number", "items",
                        "status"], {
        "order_id": OID, "store_id": OID, "package_number": STR,
        "items": {"bsonType": "array", "items": {"bsonType": "object",
                  "required": ["product_id", "quantity"],
                  "properties": {"product_id": OID,
                                 "quantity": {"bsonType": "number",
                                              "minimum": 1}}}},
        "status": {"enum": ["PENDING", "READY", "RECEIVED", "CONSOLIDATED",
                            "DISPATCHED", "CANCELLED"]},
        "fulfillment_hub_id": NULL_OID,
        "received_at": NULL_DATE, "consolidated_at": NULL_DATE,
        "dispatched_at": NULL_DATE, **TS}),

    "carts": schema(["customer_id", "mall_id", "items", "status"], {
        "customer_id": OID, "mall_id": OID,
        "status": {"enum": ["ACTIVE", "CONVERTED", "ABANDONED"]},
        "items": {"bsonType": "array", "items": {"bsonType": "object",
                  "required": ["_id", "product_id", "store_id",
                               "product_name_snapshot", "unit_price", "quantity"],
                  "properties": {"_id": OID, "product_id": OID,
                                 "store_id": OID,
                                 "product_name_snapshot": STR,
                                 "sku_snapshot": NULL_STR,
                                 "unit_price": MONEY,
                                 "quantity": {"bsonType": "number",
                                              "minimum": 1},
                                 "total_price": MONEY}}},
        "subtotal": MONEY, "delivery_fee": MONEY, "total": MONEY, **TS}),

    "orders": schema(["order_number", "customer_id", "mall_id", "pricing",
                      "delivery_address_snapshot", "merchants",
                      "payment_status", "order_status"], {
        "order_number": STR, "customer_id": OID, "mall_id": OID,
        "pricing": {"bsonType": "object",
                    "required": ["subtotal", "delivery_fee", "platform_fee",
                                 "discount", "total", "currency"],
                    "properties": {"subtotal": MONEY, "delivery_fee": MONEY,
                                   "platform_fee": MONEY, "discount": MONEY,
                                   "total": MONEY, "currency": STR}},
        "delivery_address_snapshot": ADDR_SNAPSHOT,
        "merchants": {"bsonType": "array", "minItems": 1,
                      "items": MERCHANT_ALLOC},
        "payment_status": {"enum": ["PENDING_PAYMENT", "PAID", "REFUND_PENDING",
                                    "PARTIALLY_REFUNDED", "REFUNDED",
                                    "FAILED"]},
        "order_status": {"enum": ["PENDING", "PROCESSING", "PARTIALLY_READY",
                                  "READY_FOR_DELIVERY", "OUT_FOR_DELIVERY",
                                  "DELIVERED", "CANCELLED"]},
        **TS}),

    "payments": schema(["order_id", "customer_id", "amount", "currency",
                        "status"], {
        "order_id": OID, "customer_id": OID,
        "amount": MONEY, "currency": STR,
        "status": {"enum": ["PENDING", "SUCCESS", "FAILED", "CANCELLED"]},
        "payment_method": {"enum": ["CARD", "INSTANT_EFT", "MOBILE_WALLET",
                                    "CASH_ON_DELIVERY"]},
        "provider": NULL_STR, "provider_transaction_id": NULL_STR,
        "idempotency_key": NULL_STR,
        "paid_at": NULL_DATE, **TS}),

    "payment_splits": schema(["payment_id", "order_id", "store_id",
                              "gross_amount", "platform_fee", "net_amount",
                              "status"], {
        "payment_id": OID, "order_id": OID, "store_id": OID,
        "gross_amount": MONEY, "platform_fee": MONEY, "net_amount": MONEY,
        "status": {"enum": ["PENDING", "HELD", "RELEASED", "REFUNDED"]},
        "released_at": NULL_DATE, **TS}),

    "refunds": schema(["payment_id", "order_id", "amount", "reason", "status"], {
        "payment_id": OID, "order_id": OID, "amount": MONEY,
        "reason": {"enum": ["ITEM_UNAVAILABLE", "CUSTOMER_REQUEST", "DAMAGED",
                            "ORDER_CANCELLED", "OTHER"]},
        "status": {"enum": ["PENDING", "PROCESSING", "PROCESSED",
                            "REJECTED", "FAILED"]},
        "provider_refund_id": NULL_STR, **TS}),

    "deliveries": schema(["order_id", "status"], {
        "order_id": OID,
        "driver_id": NULL_OID, "runner_id": NULL_OID,   # XOR: app layer
        "vehicle_id": NULL_OID, "pickup": GEO_NULL, "dropoff": GEO_NULL,
        "status": {"enum": ["PENDING", "ASSIGNED", "PICKED_UP",
                            "OUT_FOR_DELIVERY", "DELIVERED", "FAILED",
                            "CANCELLED"]},
        "estimated_delivery_time": NULL_DATE, **TS}),

    "delivery_tracking": schema(["delivery_id", "status", "timestamp"], {
        "delivery_id": OID,
        "status": {"enum": ["ASSIGNED", "PICKED_UP", "AT_HUB",
                            "OUT_FOR_DELIVERY", "DRIVER_ARRIVED",
                            "DELIVERED", "FAILED"]},
        "location": GEO_NULL, "notes": NULL_STR, "timestamp": DATE}),

    "drivers": schema(["user_id", "status", "is_active"], {
        "user_id": OID, "vehicle_id": NULL_OID,
        "status": {"enum": ["AVAILABLE", "ON_DELIVERY", "OFFLINE"]},
        "current_location": GEO_NULL, "is_active": BOOL, **TS}),

    "runners": schema(["user_id", "status", "is_active"], {
        "user_id": OID,
        "status": {"enum": ["AVAILABLE", "ON_DELIVERY", "OFFLINE"]},
        "current_location": GEO_NULL, "is_active": BOOL, **TS}),

    "vehicles": schema(["registration_number", "type", "driver_id",
                        "is_active"], {
        "registration_number": STR,
        "type": {"enum": ["MOTORCYCLE", "CAR", "BAKKIE", "VAN", "TRUCK"]},
        "driver_id": OID, "is_active": BOOL, **TS}),

    "qr_codes": schema(["entity_type", "entity_id", "code", "status",
                        "created_at"], {
        "entity_type": {"enum": ["ORDER", "PACKAGE", "DELIVERY"]},
        "entity_id": OID, "code": STR,
        "status": {"enum": ["ACTIVE", "SCANNED", "EXPIRED", "REVOKED"]},
        "expires_at": NULL_DATE, "scanned_at": NULL_DATE, "created_at": DATE}),

    "notifications": schema(["user_id", "type", "title", "is_read",
                             "created_at"], {
        "user_id": OID,
        "type": {"enum": ["ORDER_STATUS", "PAYMENT", "DELIVERY", "SYSTEM"]},
        "title": STR, "message": NULL_STR,
        "reference": {"bsonType": ["object", "null"],
                      "properties": {"entity_type": STR, "entity_id": OID}},
        "is_read": BOOL, "read_at": NULL_DATE, "created_at": DATE}),

    "reviews": schema(["customer_id", "store_id", "order_id", "rating"], {
        "customer_id": OID, "store_id": OID, "order_id": OID,
        "rating": {"bsonType": "number", "minimum": 1, "maximum": 5},
        "comment": NULL_STR, **TS}),

    "audit_logs": schema(["action", "entity_type", "entity_id", "timestamp"], {
        "user_id": NULL_OID, "action": STR, "entity_type": STR,
        "entity_id": OID, "changes": {"bsonType": ["object", "null"]},
        "timestamp": DATE}),

    "wallets": schema(["user_id", "balance", "currency"], {
        "user_id": OID, "balance": MONEY, "currency": STR, **TS}),

    "wallet_transactions": schema(["user_id", "type", "amount", "created_at"], {
        "user_id": OID,
        "type": {"enum": ["TOPUP", "PAYMENT", "REFUND"]},
        "amount": MONEY, "ref": NULL_STR, "order_id": NULL_OID,
        "created_at": DATE}),
}
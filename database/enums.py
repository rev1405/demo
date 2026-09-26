"""Centralized status definitions + legal state transitions.
Services enforce transitions; MongoDB stores the resulting state.
MUST stay in sync with the literal lists in database/validators.py."""
from enum import Enum


class Role(str, Enum):
    CUSTOMER = "CUSTOMER"
    MALL_ADMIN = "MALL_ADMIN"
    STORE_MANAGER = "STORE_MANAGER"
    STORE_STAFF = "STORE_STAFF"
    FULFILLMENT_STAFF = "FULFILLMENT_STAFF"
    DRIVER = "DRIVER"
    RUNNER = "RUNNER"
    SYSTEM_ADMIN = "SYSTEM_ADMIN"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PARTIALLY_READY = "PARTIALLY_READY"
    READY_FOR_DELIVERY = "READY_FOR_DELIVERY"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class FulfillmentStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY = "READY"
    HANDED_TO_DRIVER = "HANDED_TO_DRIVER"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class DeliveryStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    PICKED_UP = "PICKED_UP"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


ORDER_TRANSITIONS = {
    OrderStatus.PENDING:            {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING:         {OrderStatus.PARTIALLY_READY,
                                     OrderStatus.READY_FOR_DELIVERY,
                                     OrderStatus.CANCELLED},
    OrderStatus.PARTIALLY_READY:    {OrderStatus.READY_FOR_DELIVERY,
                                     OrderStatus.CANCELLED},
    OrderStatus.READY_FOR_DELIVERY: {OrderStatus.OUT_FOR_DELIVERY,
                                     OrderStatus.CANCELLED},
    OrderStatus.OUT_FOR_DELIVERY:   {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED:          set(),
    OrderStatus.CANCELLED:          set(),
}

FULFILLMENT_TRANSITIONS = {
    FulfillmentStatus.PENDING:          {FulfillmentStatus.ACCEPTED,
                                         FulfillmentStatus.CANCELLED},
    FulfillmentStatus.ACCEPTED:         {FulfillmentStatus.PREPARING,
                                         FulfillmentStatus.CANCELLED},
    FulfillmentStatus.PREPARING:        {FulfillmentStatus.READY,
                                         FulfillmentStatus.CANCELLED},
    FulfillmentStatus.READY:            {FulfillmentStatus.HANDED_TO_DRIVER,
                                         FulfillmentStatus.CANCELLED},
    FulfillmentStatus.HANDED_TO_DRIVER: {FulfillmentStatus.COMPLETED},
    FulfillmentStatus.COMPLETED:        set(),
    FulfillmentStatus.CANCELLED:        set(),
}

DELIVERY_TRANSITIONS = {
    DeliveryStatus.PENDING:          {DeliveryStatus.ASSIGNED, DeliveryStatus.CANCELLED},
    DeliveryStatus.ASSIGNED:         {DeliveryStatus.PICKED_UP, DeliveryStatus.CANCELLED},
    DeliveryStatus.PICKED_UP:        {DeliveryStatus.OUT_FOR_DELIVERY},
    DeliveryStatus.OUT_FOR_DELIVERY: {DeliveryStatus.DELIVERED, DeliveryStatus.FAILED},
    DeliveryStatus.DELIVERED:        set(),
    DeliveryStatus.FAILED:           {DeliveryStatus.ASSIGNED},
    DeliveryStatus.CANCELLED:        set(),
}
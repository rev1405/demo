"""Serialize MongoDB documents for JSON responses.
Decimal128 -> float, ObjectId -> str, datetime -> ISO 8601.
password_hash stripped at the serializer boundary. [SSDLC: data minimisation]"""
from datetime import date, datetime

from bson import ObjectId
from bson.decimal128 import Decimal128


def clean(x):
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items() if k != "password_hash"}
    if isinstance(x, (list, tuple)):
        return [clean(i) for i in x]
    if isinstance(x, Decimal128):
        return float(x.to_decimal())
    if isinstance(x, ObjectId):
        return str(x)
    if isinstance(x, (datetime, date)):
        return x.isoformat()
    return x

def to_float(x):
    return float(x.to_decimal()) if isinstance(x, Decimal128) else float(x)

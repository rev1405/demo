# =====================================================================
# DATABASE CONNECTION POINT - the only file that talks to MongoDB at
# the driver level. Every service/router imports get_db() from here.
#
# Flow:  routers -> services -> get_db() -> MongoDB "localyz"
# Collections + validators: database/migrations/001_initial_setup.py
# Indexes:                  database/migrations/002_add_indexes.py
# Wallets extension:        database/migrations/003_wallets_and_payment_enum.py
# =====================================================================
import os
from pymongo import MongoClient

# Read URI from environment
mongo_uri = os.getenv("MONGODB_URI")
_client = None

def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(mongo_uri, appname="mallhaul")
    return _client

def get_db():
    """Call this in services: db = get_db()."""
    return get_client()["mallhaul_db"]

def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None

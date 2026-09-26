"""Usage: python -m database.migrations.runner"""
from datetime import datetime, timezone
from importlib import import_module

from app.core.database import get_db

MIGRATIONS = ["001_initial_setup", "002_add_indexes"]


def run():
    db = get_db()
    applied = {d["migration"] for d in db.schema_migrations.find()}
    for name in MIGRATIONS:
        if name in applied:
            print(f"skip  {name}")
            continue
        print(f"run   {name}")
        import_module(f"database.migrations.{name}").up(db)
        db.schema_migrations.insert_one(
            {"migration": name, "applied_at": datetime.now(timezone.utc)})
    print("migrations complete")


if __name__ == "__main__":
    run()
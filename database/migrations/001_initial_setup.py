from pymongo.errors import CollectionInvalid

from database.validators import VALIDATORS

UNVALIDATED = ["counters", "schema_migrations"]


def up(db):
    for name, validator in VALIDATORS.items():
        try:
            db.create_collection(name, validator=validator,
                                 validationLevel="moderate")
            print(f"  created {name}")
        except CollectionInvalid:
            db.command("collMod", name, validator=validator,
                       validationLevel="moderate")
            print(f"  updated {name}")
    for name in UNVALIDATED:
        try:
            db.create_collection(name)
            print(f"  created {name}")
        except CollectionInvalid:
            print(f"  exists  {name}")
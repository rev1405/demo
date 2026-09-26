from database.indexes import create_all


def up(db):
    create_all(db)
    print("  indexes created")
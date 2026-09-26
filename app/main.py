from pymongo import MongoClient
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

# Serve all files in frontend/ as static HTML
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")



# 🔗 Replace with your actual Atlas connection string
MONGO_URI ="mongodb+srv://Tisetso:tisetso@tisetso.dahzmcu.mongodb.net/appName=Tisetso" 

# Connect to MongoDB Atlas
client = MongoClient(MONGO_URI)

# Pick your database
db = client["mallhaul_db"]
# Collections
users = db["users"]
catalog = db["catalog"]
cart = db["cart"]
orders = db["orders"]
wallet = db["wallet"]

# ✅ Test connection (ping)
try:
    client.admin.command("ping")
    print("✅ Connected to MongoDB Atlas")
except Exception as e:
    print("❌ Connection failed:", e)


# Example operations
def add_user(name, email):
    users.insert_one({"name": name, "email": email})
    print(f"User {name} added.")

def list_users():
    for u in users.find({}, {"_id": 0}):
        print(u)

def add_item_to_catalog(item_name, price):
    catalog.insert_one({"item": item_name, "price": price})
    print(f"Item {item_name} added to catalog.")

def create_order(user_email, item_name):
    orders.insert_one({"user": user_email, "item": item_name, "status": "pending"})
    print(f"Order created for {user_email} → {item_name}")


# Demo run
if __name__ == "__main__":
    add_user("Tisetso", "tisetso@example.com")
    list_users()
    add_item_to_catalog("Sneakers", 1200)
    create_order("tisetso@example.com", "Sneakers")

from fastapi import FastAPI, Form
from fastapi.staticfiles import StaticFiles
from pymongo import MongoClient
import bcrypt

app = FastAPI()

# Serve all files in frontend/ as static HTML
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")



# 🔗 Replace with your actual Atlas connection string
MONGO_URI = "mongodb+srv://Tisetso:tisetso@tisetso.dahzmcu.mongodb.net/mallhaul_db?retryWrites=true&w=majority" 

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

# ✅ Register route
@app.post("/api/register")
async def register(
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    role: str = Form(...)
):
    if password != confirm_password:
        return {"error": "Passwords do not match"}

    if users.find_one({"email": email}):
        return {"error": "User already exists"}

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    users.insert_one({"name": name, "email": email, "password": hashed_pw, "role": role})
    return {"message": "User registered successfully"}

# ✅ Login route
@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    user = users.find_one({"email": email})
    if not user:
        return {"error": "User not found"}

    if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return {"message": f"Welcome back, {user['name']}!"}
    else:
        return {"error": "Invalid credentials"}

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


from flask import Flask, render_template, request, session
from pymongo import MongoClient
import bcrypt

app = Flask(__name__)
app.secret_key = "your_generated_secret_key"

client = MongoClient("mongodb+srv://Tisetso:tisetso@tisetso.dahzmcu.mongodb.net/user_db?retryWrites=true&w=majority")
db = client["user_db"]
users = db["users"]

@app.route("/")
def index():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
@app.route("/register", methods=["POST"])
def register_user():
    name = request.form["name"]
    id_number = request.form["id_number"]
    email = request.form["email"]
    role = request.form["role"]
    password = request.form["password"]

    # Check if user already exists
    if users.find_one({"email": email}):
        return "User with this email already exists!"

    # Hash password securely
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    # Save all details
    users.insert_one({
        "name": name,
        "id_number": id_number,
        "email": email,
        "role": role,
        "password": hashed_pw
    })

    return f"User {name} registered successfully! <br><br><a href='/login_page'>Go to Login</a>"

@app.route("/login_page")
def login_page():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login():
    name = request.form["name"]
    password = request.form["password"]

    user = users.find_one({"name": name})
    if not user:
        return "User not found! <br><br><a href='/login_page'>Try again</a>"

    if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        session["user"] = name
        return f"Welcome back, {name}! You are now logged in."
    else:
        return "Invalid credentials! <br><br><a href='/login_page'>Try again</a>"

if __name__ == "__main__":
    app.run(debug=True)

import json
import os
from werkzeug.security import generate_password_hash, check_password_hash
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_FILE = os.path.join(_BASE_DIR, "data", "users.json")

def load_users():
    #Loads the full users dict from disk. Returns {} if no file exists yet.
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    #Writes the full users dict back to disk.
    os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def username_taken(username):
    return username in load_users()

def create_user(username, password):
    #Registers a new user.
    username = username.strip()
    if not username:
        return False, "Username cannot be blank."
    if not password:
        return False, "Password cannot be blank."

    users = load_users()
    if username in users:
        return False, "That username is already taken."

    users[username] = {"password_hash": generate_password_hash(password)}
    save_users(users)
    return True, None

def verify_user(username, password):
    users = load_users()
    record = users.get(username)
    if not record:
        return False
    return check_password_hash(record["password_hash"], password)

import sqlite3
import hashlib
from datetime import datetime, timezone

DB_NAME = "astrology_app.db"

def init_db():
    """Initialize SQLite database (fallback for local development)"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    # Users Table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT)''')
    
    # Profiles Table
    c.execute('''CREATE TABLE IF NOT EXISTS profiles
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  username TEXT, 
                  profile_name TEXT, 
                  dob TEXT, 
                  tob TEXT, 
                  city TEXT,
                  FOREIGN KEY(username) REFERENCES users(username))''')
    
    # Conversations Table
    c.execute('''CREATE TABLE IF NOT EXISTS conversations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  title TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(username) REFERENCES users(username))''')
    
    # Chats Table
    c.execute('''CREATE TABLE IF NOT EXISTS chats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT,
                  role TEXT,
                  content TEXT,
                  conversation_id INTEGER,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY(username) REFERENCES users(username),
                  FOREIGN KEY(conversation_id) REFERENCES conversations(id))''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# SQLite functions (for local development)
def add_user_sqlite(username, password):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user_sqlite(username, password):
    init_db()
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, hash_password(password)))
    data = c.fetchone()
    conn.close()
    return data

def save_profile_sqlite(username, profile_name, dob, tob, city):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO profiles (username, profile_name, dob, tob, city) VALUES (?, ?, ?, ?, ?)", 
              (username, profile_name, dob, tob, city))
    conn.commit()
    conn.close()

def get_user_profiles_sqlite(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT profile_name, dob, tob, city FROM profiles WHERE username = ?", (username,))
    data = c.fetchall()
    conn.close()
    return data

def create_conversation_sqlite(username, title="New Chat"):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO conversations (username, title) VALUES (?, ?)", (username, title))
    conn.commit()
    new_id = str(c.lastrowid)
    conn.close()
    return new_id

def get_user_conversations_sqlite(username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT id, title, created_at FROM conversations WHERE username = ? ORDER BY id DESC", (username,))
    data = c.fetchall()
    conn.close()
    return [(str(c[0]), c[1], str(c[2])) for c in data]

def delete_conversation_sqlite(conversation_id):
    if not conversation_id: return
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM chats WHERE conversation_id = ?", (conversation_id,))
    c.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    conn.commit()
    conn.close()

def save_chat_sqlite(username, role, content, conversation_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO chats (username, role, content, conversation_id) VALUES (?, ?, ?, ?)", 
              (username, role, content, conversation_id))
    conn.commit()
    conn.close()

def get_chat_history_sqlite(conversation_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT role, content FROM chats WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,))
    data = c.fetchall()
    conn.close()
    return [{"role": r, "content": c} for r, c in data]

def clear_chat_history_sqlite(username):
    pass

# MongoDB functions (for cloud deployment) - same as before
try:
    from bson.objectid import ObjectId
    import pymongo
    MONGO_AVAILABLE = True
except ImportError:
    MONGO_AVAILABLE = False

def add_user_mongo(db, username, password):
    users = db.users
    if users.find_one({"username": username}):
        return False
    users.insert_one({"username": username, "password": hash_password(password)})
    return True

def login_user_mongo(db, username, password):
    users = db.users
    user = users.find_one({"username": username, "password": hash_password(password)})
    return user

def save_profile_mongo(db, username, profile_name, dob, tob, city):
    profiles = db.profiles
    profiles.insert_one({
        "username": username,
        "profile_name": profile_name,
        "dob": dob,
        "tob": tob,
        "city": city
    })

def get_user_profiles_mongo(db, username):
    profiles = db.profiles
    data = list(profiles.find({"username": username}))
    return [(p["profile_name"], p["dob"], p["tob"], p["city"]) for p in data]

def create_conversation_mongo(db, username, title="New Chat"):
    conversations = db.conversations
    result = conversations.insert_one({
        "username": username,
        "title": title,
        "created_at": datetime.now(timezone.utc)
    })
    return str(result.inserted_id)

def get_user_conversations_mongo(db, username):
    conversations = db.conversations
    data = list(conversations.find({"username": username}).sort("_id", -1))
    return [(str(c["_id"]), c["title"], str(c["created_at"])) for c in data]

def delete_conversation_mongo(db, conversation_id):
    if not conversation_id: return
    try:
        oid = ObjectId(conversation_id)
        db.chats.delete_many({"conversation_id": conversation_id})
        db.conversations.delete_one({"_id": oid})
    except Exception:
        pass

def save_chat_mongo(db, username, role, content, conversation_id):
    chats = db.chats
    chats.insert_one({
        "username": username,
        "role": role,
        "content": content,
        "conversation_id": conversation_id,
        "timestamp": datetime.now(timezone.utc)
    })

def get_chat_history_mongo(db, conversation_id):
    chats = db.chats
    data = list(chats.find({"conversation_id": conversation_id}).sort("timestamp", 1))
    return [{"role": c["role"], "content": c["content"]} for c in data]

def clear_chat_history_mongo(db, username):
    pass

# Wrapper functions that route to SQLite or MongoDB
def add_user(db_or_none, username, password):
    if db_or_none is None:
        return add_user_sqlite(username, password)
    return add_user_mongo(db_or_none, username, password)

def login_user(db_or_none, username, password):
    if db_or_none is None:
        return login_user_sqlite(username, password)
    return login_user_mongo(db_or_none, username, password)

def save_profile(db_or_none, username, profile_name, dob, tob, city):
    if db_or_none is None:
        return save_profile_sqlite(username, profile_name, dob, tob, city)
    return save_profile_mongo(db_or_none, username, profile_name, dob, tob, city)

def get_user_profiles(db_or_none, username):
    if db_or_none is None:
        return get_user_profiles_sqlite(username)
    return get_user_profiles_mongo(db_or_none, username)

def create_conversation(db_or_none, username, title="New Chat"):
    if db_or_none is None:
        return create_conversation_sqlite(username, title)
    return create_conversation_mongo(db_or_none, username, title)

def get_user_conversations(db_or_none, username):
    if db_or_none is None:
        return get_user_conversations_sqlite(username)
    return get_user_conversations_mongo(db_or_none, username)

def delete_conversation(db_or_none, conversation_id):
    if db_or_none is None:
        return delete_conversation_sqlite(conversation_id)
    return delete_conversation_mongo(db_or_none, conversation_id)

def save_chat(db_or_none, username, role, content, conversation_id):
    if db_or_none is None:
        return save_chat_sqlite(username, role, content, conversation_id)
    return save_chat_mongo(db_or_none, username, role, content, conversation_id)

def get_chat_history(db_or_none, conversation_id):
    if db_or_none is None:
        return get_chat_history_sqlite(conversation_id)
    return get_chat_history_mongo(db_or_none, conversation_id)

def clear_chat_history(db_or_none, username):
    if db_or_none is None:
        return clear_chat_history_sqlite(username)
    return clear_chat_history_mongo(db_or_none, username)

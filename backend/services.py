import os
import secrets
from datetime import datetime, timedelta, timezone
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))
db = client["chatbot_db"]
collection = db["chat_history"]
users = db["users"]
user_sessions = db["user_sessions"]  
checkpoints = db["checkpoints"]  # LangGraph's MongoDBSaver collection (agent.py)
checkpoint_writes = db["checkpoint_writes"]  # LangGraph's companion writes collection
auth_tokens = db["auth_tokens"]  # maps an opaque session token -> user_email, for login persistence

TOKEN_TTL = timedelta(days=7)

PERSONALITY = "You are a friendly assistant for NetSol Technologies. Answer clearly and concisely. Do not use markdown formatting like bold or asterisks or inverted commas."

def delete_session(session_id):
    user_sessions.delete_many({"session_id": session_id})
    collection.delete_many({"session_id": session_id})
    checkpoints.delete_many({"thread_id": session_id})
    checkpoint_writes.delete_many({"thread_id": session_id})
    return {"message": "Session deleted successfully"}


def register_session(user_email, session_id, title=None):
    """Records that this session belongs to this user, the first time a
    message is sent in it. Upserts the title only if not already set, so
    re-sending messages in the same session doesn't keep overwriting it."""
    existing = user_sessions.find_one({"user_email": user_email, "session_id": session_id})
    if existing:
        return
    user_sessions.insert_one({
        "user_email": user_email,
        "session_id": session_id,
        "title": title or "New chat",
    })


def get_user_sessions(user_email):
    """Returns this user's sessions, most recently created first."""
    docs = user_sessions.find({"user_email": user_email}).sort("_id", -1)
    return [{"session_id": d["session_id"], "title": d["title"]} for d in docs]


def create_auth_token(user_email):
    """Issues a random, unguessable token for this user and stores the
    mapping server-side. The frontend keeps only this token (e.g. in the
    URL) - never the email directly - so a leaked/shared URL doesn't hand
    over the account the way storing the raw email would."""
    token = secrets.token_urlsafe(32)
    auth_tokens.insert_one({
        "token": token,
        "user_email": user_email,
        "expires_at": datetime.now(timezone.utc) + TOKEN_TTL,
    })
    return token


def resolve_auth_token(token):
    """Returns the user_email for a valid, non-expired token, or None."""
    doc = auth_tokens.find_one({"token": token})
    if not doc:
        return None
    expires_at = doc["expires_at"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        auth_tokens.delete_one({"token": token})
        return None
    return doc["user_email"]


def revoke_auth_token(token):
    """Invalidates a token immediately (used on logout)."""
    auth_tokens.delete_one({"token": token})
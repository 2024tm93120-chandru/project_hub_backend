# main.py
import sqlite3
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

import db
from gemini_client import ask_gemini_for_intent

app = FastAPI(title="Project Hub Assistant")

# Initialise DB tables
db.init_db()

# In-memory conversation context
conversation_state: Dict[str, Any] = {}


# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],     # Allow all for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    text: str
    language: Optional[str] = "en"
    session_id: Optional[str] = "user1"   # FIX: prevent attribute error


# ---------------------------
# Helper for saving items
# ---------------------------
def save_to_db(type: str, fields: dict):
    conn = sqlite3.connect("projecthub.db")
    c = conn.cursor()

    if type == "bug":
        c.execute("""
            INSERT INTO bugs (title, description, severity, steps)
            VALUES (?,?,?,?)
        """, (fields["title"], fields["description"], fields["severity"], fields["steps"]))

    elif type == "requirement":
        c.execute("""
            INSERT INTO requirements (title, description, priority)
            VALUES (?,?,?)
        """, (fields["title"], fields["description"], fields["priority"]))

    elif type == "query":
        c.execute("""
            INSERT INTO queries (title, description, assigned_to)
            VALUES (?,?,?)
        """, (fields["title"], fields["description"], fields["assigned_to"]))

    conn.commit()
    conn.close()


# =====================================================
# MAIN CHAT ENDPOINT
# =====================================================
@app.post("/chat")
async def chat(req: ChatRequest):
    user_id = req.session_id or "user1"
    language = req.language or "en"
    text = req.text.strip()

    # STEP 1 — Check if user is already in a filling flow (bug / requirement / query)
    if user_id in conversation_state and conversation_state[user_id] is not None:
        state = conversation_state[user_id]
        flow = state["intent"]
        next_field = state["next_field"]

        # Store user answer
        state["fields"][next_field] = text

        # BUG FLOW
        if flow == "create_bug":
            if next_field == "title":
                state["next_field"] = "description"
                return {"reply": "Got it! Please describe the bug."}

            elif next_field == "description":
                state["next_field"] = "severity"
                return {"reply": "Thanks! What is the severity? (Low, Medium, High)"}

            elif next_field == "severity":
                state["next_field"] = "steps"
                return {"reply": "Understood. What are the steps to reproduce it?"}

            elif next_field == "steps":
                save_to_db("bug", state["fields"])
                conversation_state[user_id] = None
                return {"reply": "Bug report created successfully!"}

        # REQUIREMENT FLOW
        if flow == "create_requirement":
            if next_field == "title":
                state["next_field"] = "description"
                return {"reply": "Okay! Please describe the requirement."}

            elif next_field == "description":
                state["next_field"] = "priority"
                return {"reply": "What is the priority? (Low, Medium, High)"}

            elif next_field == "priority":
                save_to_db("requirement", state["fields"])
                conversation_state[user_id] = None
                return {"reply": "Requirement created successfully!"}

        # QUERY FLOW
        if flow == "create_query":
            if next_field == "title":
                state["next_field"] = "description"
                return {"reply": "Please describe the query."}

            elif next_field == "description":
                state["next_field"] = "assigned_to"
                return {"reply": "Who should this be assigned to?"}

            elif next_field == "assigned_to":
                save_to_db("query", state["fields"])
                conversation_state[user_id] = None
                return {"reply": "Query created successfully!"}

    # STEP 2 — Normal message: Use Gemini to understand intent
    gem = ask_gemini_for_intent(text, req.language)
    intent = gem["intent"]
    entities = gem["entities"]
    reply = gem["reply"]
    action = gem["action"]
    print(req.language)
    # -------------------------
    # INTENT: CREATE BUG
    # -------------------------
    if intent == "report_bug":
        conversation_state[user_id] = {
            "intent": "create_bug",
            "fields": {"title": None, "description": None, "severity": None, "steps": None},
            "next_field": "title"
        }
        return {"reply": "Sure, what is the bug title?"}

    # -------------------------
    # INTENT: CREATE REQUIREMENT
    # -------------------------
    if intent == "create_requirement":
        conversation_state[user_id] = {
            "intent": "create_requirement",
            "fields": {"title": None, "description": None, "priority": None},
            "next_field": "title"
        }
        return {"reply": "Sure, what is the requirement title?"}

    # -------------------------
    # INTENT: CREATE QUERY
    # -------------------------
    if intent == "raise_query":
        conversation_state[user_id] = {
            "intent": "create_query",
            "fields": {"title": None, "description": None, "assigned_to": None},
            "next_field": "title"
        }
        return {"reply": "Okay! What is the query title?"}

    # -------------------------
    # INTENT: LIST ITEMS
    # -------------------------
    if intent == "get_items" and entities.get("type"):
        item_type = entities["type"]
        if item_type == "requirements":
            return {"items": db.list_requirements(), "reply": reply}
        if item_type == "bugs":
            return {"items": db.list_bugs(), "reply": reply}
        if item_type == "queries":
            return {"items": db.list_queries(), "reply": reply}

    # -------------------------
    # SMALLTALK / FALLBACK
    # -------------------------
    return {"reply": reply or "I am here to help!"}


# =====================================================
# NORMAL REST ENDPOINTS
# =====================================================
@app.get("/requirement/list")
def list_requirements():
    return {"items": db.list_requirements()}

@app.get("/bug/list")
def list_bugs():
    return {"items": db.list_bugs()}

@app.get("/query/list")
def list_queries():
    return {"items": db.list_queries()}

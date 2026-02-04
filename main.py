from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
import re
import random
import requests

app = FastAPI()

API_KEY = "test123"
CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"


# ===================== MODELS =====================

class Message(BaseModel):
    sender: str
    text: str
    timestamp: int

class Metadata(BaseModel):
    channel: str = None
    language: str = None
    locale: str = None

class HoneypotRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: list = []
    metadata: Metadata = None


# ===================== MEMORY =====================

sessions = {}


# ===================== CONSTANTS =====================

SCAM_KEYWORDS = ["kyc", "blocked", "urgent", "verify", "otp", "upi", "account", "bank"]

GOAL_QUESTIONS = {
    "upi": [
        "Where should I send the money?",
        "Can you share the UPI ID again?"
    ],
    "link": [
        "Which website should I open?",
        "Where is the verification link?"
    ],
    "phone": [
        "Is there any customer care number?",
        "Whom should I call for help?"
    ],
    "bank": [
        "Which bank is this message from?",
        "Is this from SBI or HDFC?"
    ]
}

FALLBACK_REPLIES = [
    "I am confused, can you explain clearly?",
    "Please help me step by step",
    "I don’t understand what to do now"
]


# ===================== HELPERS =====================

def detect_scam(text):
    return any(word in text.lower() for word in SCAM_KEYWORDS)


def extract_links(text):
    return re.findall(r'https?://\S+', text)


def extract_upi(text):
    return re.findall(r'\b[\w.-]+@[\w.-]+\b', text)


def extract_phone(text):
    return re.findall(r'\+91\d{10}|\b\d{10}\b', text)


def extract_bank(text):
    banks = ["sbi", "hdfc", "icici", "axis", "pnb"]
    found = []
    for b in banks:
        if b in text.lower():
            found.append(b.upper())
    return found


def extract_keywords(text):
    return [k for k in SCAM_KEYWORDS if k in text.lower()]


# ===================== SESSION =====================

def init_session(session_id):
    sessions[session_id] = {
        "messages": 0,
        "bankAccounts": [],
        "upiIds": [],
        "phishingLinks": [],
        "phoneNumbers": [],
        "banks": [],
        "suspiciousKeywords": []
    }


# ===================== AGENT BRAIN =====================

def choose_next_goal(session):
    if not session["upiIds"]:
        return "upi"
    if not session["phishingLinks"]:
        return "link"
    if not session["phoneNumbers"]:
        return "phone"
    if not session["banks"]:
        return "bank"
    return None


def generate_smart_reply(session):
    goal = choose_next_goal(session)

    if goal:
        return random.choice(GOAL_QUESTIONS[goal])

    return random.choice(FALLBACK_REPLIES)


def enough_intelligence(session):
    return (
        len(session["upiIds"]) > 0 and
        len(session["phishingLinks"]) > 0
    )


# ===================== CALLBACK =====================

def send_final_callback(session_id):
    s = sessions[session_id]

    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": s["messages"],
        "extractedIntelligence": {
            "bankAccounts": s["bankAccounts"],
            "upiIds": s["upiIds"],
            "phishingLinks": s["phishingLinks"],
            "phoneNumbers": s["phoneNumbers"],
            "suspiciousKeywords": list(set(s["suspiciousKeywords"]))
        },
        "agentNotes": "Autonomous agent extracted scam intelligence via adaptive questioning"
    }

    try:
        requests.post(CALLBACK_URL, json=payload, timeout=5)
    except:
        print("Callback skipped (local testing)")


# ===================== API =====================

@app.post("/honeypot")
def honeypot(req: HoneypotRequest, x_api_key: str = Header(None)):

    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")

    session_id = req.sessionId
    text = req.message.text

    if session_id not in sessions:
        init_session(session_id)

    s = sessions[session_id]
    s["messages"] += 1

    # Detect scam
    scam_detected = detect_scam(text)

    # Extract intelligence
    s["phishingLinks"].extend(extract_links(text))
    s["upiIds"].extend(extract_upi(text))
    s["phoneNumbers"].extend(extract_phone(text))
    s["banks"].extend(extract_bank(text))
    s["suspiciousKeywords"].extend(extract_keywords(text))

    # If enough data → send final result
    if scam_detected and enough_intelligence(s):
        send_final_callback(session_id)

    # Generate intelligent reply
    reply = generate_smart_reply(s)

    return {
        "status": "success",
        "reply": reply
    }

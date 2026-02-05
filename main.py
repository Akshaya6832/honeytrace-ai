from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import re, requests, time, random

app = FastAPI(title="AI Brain Agentic Honeypot")

API_KEY = "test123"

# =========================
# MODELS
# =========================

class Message(BaseModel):
    sender: str
    text: str
    timestamp: int

class HoneypotRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message] = []
    metadata: Optional[dict] = None


# =========================
# MEMORY
# =========================

SESSIONS = {}

# =========================
# SIGNAL INTELLIGENCE
# =========================

SIGNALS = {
    "urgency": ["urgent","immediately","now","today"],
    "threat": ["blocked","suspended","closed"],
    "payment": ["upi","pay","transfer"],
    "phishing": ["click","verify","link"],
    "impersonation": ["bank","official","support"]
}

WEIGHTS = {
    "urgency": 15,
    "threat": 20,
    "payment": 25,
    "phishing": 20,
    "impersonation": 20
}

# =========================
# EXTRACTION ENGINE
# =========================

def extract_intel(text):
    return {
        "phishingLinks": re.findall(r"https?://\S+", text),
        "upiIds": re.findall(r"\b[\w.-]+@upi\b", text),
        "phoneNumbers": re.findall(r"\+91\d{10}", text),
        "bankAccounts": re.findall(r"\b\d{9,18}\b", text)
    }


# =========================
# RISK ANALYSIS
# =========================

def detect_signals(text):
    t = text.lower()
    found=[]
    score=0

    for s,words in SIGNALS.items():
        for w in words:
            if w in t:
                found.append(s)
                score+=WEIGHTS[s]
                break

    return found, min(score,100)


# =========================
# 🧠 AI BRAIN (Reasoning Agent)
# =========================

def ai_brain_decision(session, tactics, risk):

    # Think like human agent

    if not session["confirmed"]:
        return "confuse", "I’m not sure what you mean, can you explain?"

    if risk < 50:
        return "delay", "I’m outside now, please tell me slowly"

    if "payment" in tactics:
        return "extract", "Where exactly should I send the money?"

    if "phishing" in tactics:
        return "extract", "Can you share the link again?"

    if "impersonation" in tactics:
        return "verify", "Which bank is this message from?"

    return "delay", "I am checking, please wait"


# =========================
# CALLBACK
# =========================

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

def send_final_report(session_id, intel, total, notes):
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total,
        "extractedIntelligence": intel,
        "agentNotes": notes
    }
    try:
        requests.post(CALLBACK_URL, json=payload, timeout=5)
    except:
        pass


# =========================
# AUTH
# =========================

def verify(key):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# =========================
# ROOT
# =========================

@app.get("/")
def home():
    return {
        "status":"running",
        "system":"Hybrid AI Brain Honeypot",
        "endpoint":"/honeypot",
        "docs":"/docs"
    }


# =========================
# MAIN ENDPOINT
# =========================

@app.post("/honeypot")
def honeypot(body:HoneypotRequest, x_api_key:str=Header(...)):

    verify(x_api_key)

    sid = body.sessionId
    msg = body.message.text

    if sid not in SESSIONS:
        SESSIONS[sid] = {
            "risk":0,
            "messages":0,
            "confirmed":False,
            "intelligence":{
                "bankAccounts":[],
                "upiIds":[],
                "phishingLinks":[],
                "phoneNumbers":[],
                "suspiciousKeywords":[]
            }
        }

    session = SESSIONS[sid]
    session["messages"] += 1

    tactics, score = detect_signals(msg)

    session["risk"] = max(session["risk"], score)

    if score > 40:
        session["confirmed"] = True

    session["intelligence"]["suspiciousKeywords"].extend(tactics)

    extracted = extract_intel(msg)

    for k,v in extracted.items():
        session["intelligence"][k].extend(v)

    for k in session["intelligence"]:
        session["intelligence"][k] = list(set(session["intelligence"][k]))

    # 🧠 AI Brain Response
    strategy, reply = ai_brain_decision(session, tactics, session["risk"])

    # 📤 Final callback after enough engagement
    if session["messages"] >= 6 and session["confirmed"]:
        send_final_report(
            sid,
            session["intelligence"],
            session["messages"],
            "AI Brain agent adapted tactics and extracted scam intelligence"
        )

    return {
        "status":"success",
        "sessionId": sid,
        "scamDetected": session["confirmed"],
        "riskScore": session["risk"],
        "totalMessages": session["messages"],
        "tacticsDetected": tactics,
        "agentStrategy": strategy,
        "extractedIntelligence": session["intelligence"],
        "reply": reply
    }

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import re, random, requests, time

app = FastAPI(title="Hybrid Agentic Honeypot AI")

API_KEY = "test123"

# =======================
# MODELS
# =======================

class Message(BaseModel):
    sender: str
    text: str
    timestamp: int

class HoneypotRequest(BaseModel):
    sessionId: str
    message: Message
    conversationHistory: List[Message] = []
    metadata: Optional[dict] = None


# =======================
# MEMORY
# =======================

SESSIONS = {}

# =======================
# HYBRID SIGNALS
# =======================

SIGNALS = {
    "urgency": ["urgent","immediately","now","today"],
    "threat": ["blocked","suspended","closed"],
    "payment": ["upi","transfer","pay"],
    "phishing": ["click","verify","link"],
    "impersonation": ["bank","support","official"]
}

WEIGHTS = {
    "urgency": 15,
    "threat": 20,
    "payment": 25,
    "phishing": 20,
    "impersonation": 20
}

# =======================
# EXTRACTION
# =======================

def extract_all(text):
    return {
        "phishingLinks": re.findall(r"https?://\S+", text),
        "upiIds": re.findall(r"\b[\w.-]+@upi\b", text),
        "phoneNumbers": re.findall(r"\+91\d{10}", text),
        "bankAccounts": re.findall(r"\b\d{9,18}\b", text)
    }

# =======================
# HYBRID DETECTION
# =======================

def analyze_text(text):
    found = []
    score = 0
    t = text.lower()

    for k, words in SIGNALS.items():
        for w in words:
            if w in t:
                found.append(k)
                score += WEIGHTS[k]
                break

    return found, min(score,100)


# =======================
# AGENT STRATEGY ENGINE
# =======================

def choose_strategy(risk):
    if risk < 40:
        return "confuse"
    elif risk < 70:
        return "delay"
    else:
        return "extract"


PERSONA_RESPONSES = {
    "confuse": [
        "I don’t understand what you mean",
        "Which bank are you talking about?"
    ],
    "delay": [
        "I am busy now, can you explain slowly?",
        "I will check later, please guide me properly"
    ],
    "extract": [
        "Where should I pay exactly?",
        "Can you send the link again?",
        "Which UPI ID should I use?"
    ]
}

def agent_reply(strategy):
    return random.choice(PERSONA_RESPONSES[strategy])


# =======================
# CALLBACK
# =======================

CALLBACK_URL = "https://hackathon.guvi.in/api/updateHoneyPotFinalResult"

def send_callback(session_id, intel, total_msgs, notes):
    payload = {
        "sessionId": session_id,
        "scamDetected": True,
        "totalMessagesExchanged": total_msgs,
        "extractedIntelligence": intel,
        "agentNotes": notes
    }
    try:
        requests.post(CALLBACK_URL, json=payload, timeout=5)
    except:
        pass


# =======================
# AUTH
# =======================

def verify(key):
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


# =======================
# ROOT
# =======================

@app.get("/")
def home():
    return {
        "status":"running",
        "system":"Hybrid Agentic Honeypot AI",
        "docs":"/docs"
    }


# =======================
# MAIN ENDPOINT
# =======================

@app.post("/honeypot")
def honeypot(body:HoneypotRequest, x_api_key:str=Header(...)):

    verify(x_api_key)

    sid = body.sessionId
    msg = body.message.text

    if sid not in SESSIONS:
        SESSIONS[sid] = {
            "risk":0,
            "messages":0,
            "intelligence":{
                "bankAccounts":[],
                "upiIds":[],
                "phishingLinks":[],
                "phoneNumbers":[],
                "suspiciousKeywords":[]
            },
            "confirmed":False
        }

    session = SESSIONS[sid]
    session["messages"] += 1

    tactics, score = analyze_text(msg)

    session["risk"] = max(session["risk"], score)

    if score > 40:
        session["confirmed"] = True

    session["intelligence"]["suspiciousKeywords"].extend(tactics)

    extracted = extract_all(msg)

    for k,v in extracted.items():
        session["intelligence"][k].extend(v)

    for k in session["intelligence"]:
        session["intelligence"][k] = list(set(session["intelligence"][k]))

    reply = None

    if session["confirmed"]:
        strategy = choose_strategy(session["risk"])
        reply = agent_reply(strategy)
    else:
        strategy = "none"

    # Finalize after enough turns
    if session["messages"] >= 6 and session["confirmed"]:
        send_callback(
            sid,
            session["intelligence"],
            session["messages"],
            "Hybrid system detected escalation and extracted payment intel"
        )

    return {
        "status":"success",
        "sessionId":sid,
        "scamDetected":session["confirmed"],
        "riskScore":session["risk"],
        "totalMessages":session["messages"],
        "tacticsDetected":tactics,
        "agentStrategy":strategy,
        "extractedIntelligence":session["intelligence"],
        "reply": reply
    }

# backend/app.py
import os
import sys
import uuid
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask import Flask, request, jsonify, send_from_directory, render_template

# Make sure backend package path is importable when running from repo root
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# Local imports (these files should already exist as per previous steps)
from model.llm_client import LLMClient
from services.tutor_services import TutorService
from services.session_manager import SessionManager
from db.db_manager import DBManager

app = Flask(__name__, template_folder="../frontend/template", static_folder="../frontend/static")
CORS(app)

# Global LLM client & tutor service
LLM_MODEL_NAME = os.getenv("OLLAMA_MODEL", "phi3.5")
llm_client = LLMClient(model_name=LLM_MODEL_NAME)
tutor_service = TutorService(model_name=LLM_MODEL_NAME)

# In-memory session store: session_id -> SessionManager
SESSIONS = {}

# DB manager (persistent storage)
db = DBManager()

@app.route("/start_session", methods=["POST"])
def start_session():
    """
    Start a new session.
    Optional JSON body:
    {
        "user_id": "user123",    # optional
        "starting_level": "A1"   # optional
    }
    Returns: { "session_id": "...", "difficulty": "A1" }
    """
    body = request.json or {}
    user_id = body.get("user_id", f"user_{uuid.uuid4().hex[:8]}")
    starting_level = body.get("starting_level", "A1")

    session_id = uuid.uuid4().hex
    session = SessionManager(user_id=user_id)
    session.difficulty = starting_level
    SESSIONS[session_id] = session

    return jsonify({"session_id": session_id, "difficulty": session.difficulty, "user_id": user_id})

def _parse_tutor_response(raw_text):
    """
    Parse the tutor response which follows the structure:
    **Corrected Spanish:**
    <text>

    **Explanation:**
    <text>

    **Example:**
    <text>

    **Tip:**
    <text>
    """
    # Fallback dict
    parsed = {
        "corrected": None,
        "explanation": None,
        "example": None,
        "tip": None,
        "raw": raw_text
    }

    # Simple split by headings
    try:
        # Normalize headings (allow some small variations)
        headings = ["**Corrected Spanish:**", "**Explanation:**", "**Example:**", "**Tip:**"]
        remaining = raw_text
        for i, h in enumerate(headings):
            if h in remaining:
                parts = remaining.split(h, 1)
                # parts[1] contains the rest; find next heading if present
                next_part = parts[1]
                # find next heading position
                next_heading_pos = None
                next_text = next_part
                for nh in headings[i+1:]:
                    idx = next_part.find(nh)
                    if idx != -1:
                        next_heading_pos = idx
                        break
                if next_heading_pos is not None:
                    content = next_part[:next_heading_pos].strip()
                    remaining = next_part[next_heading_pos:]
                else:
                    content = next_part.strip()
                    remaining = ""
                key = ["corrected", "explanation", "example", "tip"][i]
                parsed[key] = content
            else:
                # heading not present; leave as None
                pass
    except Exception:
        # If parsing fails, keep raw_text in raw field
        parsed["raw"] = raw_text

    return parsed

@app.route("/chat", methods=["POST"])
def chat():
    """
    Chat endpoint.
    Body:
    {
        "session_id": "...",
        "message": "user input text",
        "language": "spanish",             # optional (defaults to "spanish")
        "known_language": "English",      # optional (used for prompt building later)
        "learning_language": "Spanish"    # optional
    }
    Returns: {
        "session_id": "...",
        "response": { corrected, explanation, example, tip, raw },
        "difficulty": "A2",
        "mistake_logged": true/false
    }
    """
    body = request.json or {}
    session_id = body.get("session_id")
    user_message = body.get("message")
    language = body.get("language", "spanish")
    known_language = body.get("known_language", "English")
    learning_language = body.get("learning_language", "Spanish")

    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid or missing session_id. Start a session first."}), 400
    if not user_message:
        return jsonify({"error": "Missing message"}), 400

    session = SESSIONS[session_id]

    # Build the tutor prompt via TutorService with language parameter
    ai_raw_response = tutor_service.process_user_message(user_message, language)

    # Parse the structured response from the tutor
    parsed = _parse_tutor_response(ai_raw_response)

    # Decide if there was a mistake: if corrected exists and differs from user_message
    corrected = parsed.get("corrected") or ""
    mistake_logged = False
    severity = None

    # Basic heuristic to detect a correction: normalized compare
    def normalize_text(t): return "".join(t.lower().split()) if t else ""
    if corrected and normalize_text(corrected) != normalize_text(user_message):
        # Mark a mistake. Assign a naive severity (can be improved later)
        # If correction is short and differs slightly -> low; if many token differences -> medium/high
        user_len = len(user_message.split())
        corr_len = len(corrected.split())
        diff = abs(user_len - corr_len)
        # compute token-change heuristic
        if diff <= 1 and user_len <= 5:
            severity = "low"
        elif diff <= 3:
            severity = "medium"
        else:
            severity = "high"

        # Save mistake in DB (SessionManager will call DBManager internally)
        session.record_interaction(user_message, ai_raw_response, mistake=corrected, severity=severity)
        mistake_logged = True
    else:
        # No mistake: just record the interaction without mistake
        session.record_interaction(user_message, ai_raw_response, mistake=None, severity=None)

    # Return useful structured info
    result = {
        "session_id": session_id,
        "response": parsed,
        "difficulty": session.difficulty,
        "mistake_logged": mistake_logged,
        "severity": severity
    }
    return jsonify(result)

@app.route("/end_session", methods=["POST"])
def end_session():
    """
    End a session and return immediate summary.
    Body: { "session_id": "..." }
    """
    body = request.json or {}
    session_id = body.get("session_id")
    if not session_id or session_id not in SESSIONS:
        return jsonify({"error": "Invalid or missing session_id"}), 400

    session = SESSIONS.pop(session_id)
    summary = session.get_summary()

    return jsonify({"session_id": session_id, "summary": summary})

@app.route("/summary", methods=["GET"])
def summary():
    """
    Get aggregated mistakes from persistent DB or session.
    Query params: ?session_id=...  (optional)
    """
    session_id = request.args.get("session_id")

    # If session_id provided and still active, fetch from session
    if session_id and session_id in SESSIONS:
        summary = SESSIONS[session_id].get_summary()
        return jsonify({"session_id": session_id, "summary": summary})

    # Otherwise, fetch aggregated mistakes from DB
    rows = db.get_all_mistakes()
    # Convert to JSON-friendly list
    mistakes = []
    for r in rows:
        # DB columns: id, user_id, user_input, correction, severity, difficulty, timestamp
        if len(r) >= 7:
            mistakes.append({
                "id": r[0],
                "user_id": r[1],
                "user_input": r[2],
                "correction": r[3],
                "severity": r[4],
                "difficulty": r[5],
                "timestamp": r[6]
            })
        else:
            # backward compatibility if schema differs
            mistakes.append({"row": r})
    return jsonify({"total_mistakes": len(mistakes), "mistakes": mistakes})

@app.route("/")
def home():
    return render_template("index.html")

if __name__ == "__main__":
    # Run Flask app (development mode)
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)

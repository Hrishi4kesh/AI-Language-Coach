import time
from backend.db.db_manager import DBManager

class SessionManager:
    def __init__(self, user_id="default_user"):
        self.user_id = user_id
        self.history = []
        self.difficulty = "A1"  # starting level
        self.db = DBManager()

    def record_interaction(self, user_input, ai_response, mistake=None, severity=None):
        """Save every interaction + mistake (if any)."""

        record = {
            "timestamp": time.time(),
            "user_input": user_input,
            "ai_response": ai_response,
            "mistake": mistake,
            "severity": severity,
            "difficulty": self.difficulty
        }

        self.history.append(record)

        if mistake:
            self.db.save_mistake(self.user_id, user_input, mistake, severity, self.difficulty)

        self._update_difficulty(severity)

    def _update_difficulty(self, severity):
        """Auto-adjust difficulty based on recent mistakes."""
        if not severity:
            return

        if severity == "low":
            self.difficulty = "A2"
        elif severity == "medium":
            self.difficulty = "B1"
        elif severity == "high":
            self.difficulty = "A1"  # fallback to basics

    def get_summary(self):
        """Builds a short session summary from stored records."""

        mistakes = [h for h in self.history if h["mistake"]]
        
        summary = {
            "total_messages": len(self.history),
            "total_mistakes": len(mistakes),
            "mistake_details": mistakes,
            "final_level": self.difficulty
        }

        return summary

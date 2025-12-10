import sqlite3
import os

DB_PATH = "backend/db/mistakes.db"

class DBManager:
    def __init__(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS mistakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            user_input TEXT,
            correction TEXT,
            severity TEXT,
            difficulty TEXT,
            timestamp TEXT
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def save_mistake(self, user_id, user_input, correction, severity, difficulty):
        query = """
        INSERT INTO mistakes (user_id, user_input, correction, severity, difficulty, timestamp)
        VALUES (?, ?, ?, ?, ?, DATETIME('now'))
        """
        self.conn.execute(query, (user_id, user_input, correction, severity, difficulty))
        self.conn.commit()

    def get_all_mistakes(self):
        cursor = self.conn.cursor()   # <-- FIXED: Create cursor here
        cursor.execute("SELECT user_input, correction FROM mistakes")
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def close(self):
        self.conn.close()

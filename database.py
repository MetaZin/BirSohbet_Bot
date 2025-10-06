import sqlite3
from datetime import datetime
import os

DB_NAME = "birsohbet.db"
LOG_FILE = "birsohbet.log"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    nickname TEXT,
                    gender TEXT,
                    target_gender TEXT
                )''')
    conn.commit()
    conn.close()


def register_user(user_id, nickname, gender, target_gender):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO users (user_id, nickname, gender, target_gender) VALUES (?, ?, ?, ?)",
        (user_id, nickname, gender.lower(), target_gender.lower()),
    )
    conn.commit()
    conn.close()
    log_event(f"Kayıt -> {user_id} | {nickname} | {gender} arıyor: {target_gender}")


def get_user_preferences(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT gender, target_gender FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row if row else (None, None)


def get_gender_counts():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT gender, COUNT(*) FROM users GROUP BY gender")
    data = c.fetchall()
    conn.close()
    return {gender: count for gender, count in data}


def log_event(text):
    try:
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        line = f"{timestamp} {text}\n"
        os.makedirs(os.path.dirname(LOG_FILE) or ".", exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"[LOG HATASI] {e}")

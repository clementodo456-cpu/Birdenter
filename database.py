import os
import sqlite3
from datetime import datetime, date
import pytz

DATABASE_PATH = os.getenv("DATABASE_PATH", "./data/reminders.db")

def get_connection():
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            timezone TEXT DEFAULT 'UTC',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT NOT NULL,
            description TEXT,
            reminder_datetime TEXT NOT NULL,
            timezone TEXT NOT NULL,
            recurrence TEXT DEFAULT 'none',
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    
    conn.commit()
    conn.close()

def get_or_create_user(user_id: int, username: str, first_name: str) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        cursor.execute(
            "INSERT INTO users (user_id, username, first_name, timezone) VALUES (?, ?, ?, 'UTC')",
            (user_id, username or "", first_name or "")
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        
    conn.close()
    return dict(user)

def get_user_timezone(user_id: int) -> str:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT timezone FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["timezone"] if row else "UTC"

def set_user_timezone(user_id: int, tz_name: str) -> bool:
    try:
        pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        return False
        
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET timezone = ? WHERE user_id = ?", (tz_name, user_id))
    conn.commit()
    conn.close()
    return True

def add_reminder(user_id: int, title: str, description: str, reminder_datetime_iso: str, tz_str: str, recurrence: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO reminders (user_id, title, description, reminder_datetime, timezone, recurrence, status)
        VALUES (?, ?, ?, ?, ?, ?, 'active')
    """, (user_id, title, description, reminder_datetime_iso, tz_str, recurrence))
    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id

def get_reminder_by_id(reminder_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_active_reminders() -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM reminders WHERE status = 'active'")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_reminders(user_id: int, status: str = 'active') -> list:
    conn = get_connection()
    cursor = conn.cursor()
    if status == 'all':
        cursor.execute("SELECT * FROM reminders WHERE user_id = ? ORDER BY reminder_datetime ASC", (user_id,))
    else:
        cursor.execute("SELECT * FROM reminders WHERE user_id = ? AND status = ? ORDER BY reminder_datetime ASC", (user_id, status))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_today_reminders(user_id: int) -> list:
    user_tz_name = get_user_timezone(user_id)
    user_tz = pytz.timezone(user_tz_name)
    today_str = datetime.now(user_tz).strftime("%Y-%m-%d")
    
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM reminders 
        WHERE user_id = ? AND status = 'active' AND strftime('%Y-%m-%d', reminder_datetime) = ?
        ORDER BY reminder_datetime ASC
    """, (user_id, today_str))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_user_date_reminders(user_id: int, date_str: str) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM reminders 
        WHERE user_id = ? AND status = 'active' AND strftime('%Y-%m-%d', reminder_datetime) = ?
        ORDER BY reminder_datetime ASC
    """, (user_id, date_str))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_reminder_status(reminder_id: int, status: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, reminder_id))
    conn.commit()
    conn.close()

def update_reminder_datetime(reminder_id: int, new_datetime_iso: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE reminders SET reminder_datetime = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_datetime_iso, reminder_id))
    conn.commit()
    conn.close()

def delete_reminder(reminder_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()

def get_user_stats(user_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM reminders WHERE user_id = ?", (user_id,))
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reminders WHERE user_id = ? AND status = 'active'", (user_id,))
    active = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reminders WHERE user_id = ? AND status = 'completed'", (user_id,))
    completed = cursor.fetchone()[0]
    
    conn.close()
    return {"total": total, "active": active, "completed": completed}

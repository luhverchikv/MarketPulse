import sqlite3
import json
import os

DB_PATH = "trendscope.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
        chat_id INTEGER PRIMARY KEY,
        territory TEXT DEFAULT 'RU',
        topic TEXT DEFAULT 'AI',
        period TEXT DEFAULT '7d',
        is_active INTEGER DEFAULT 1
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS trends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER,
        source TEXT,
        data TEXT,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(chat_id) REFERENCES users(chat_id)
    )''')
    conn.commit()
    conn.close()

def save_user(chat_id, territory, topic, period):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (chat_id, territory, topic, period, is_active) VALUES (?, ?, ?, ?, 1)',
                   (chat_id, territory, topic, period))
    conn.commit()
    conn.close()

def get_active_users():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id, territory, topic, period FROM users WHERE is_active = 1')
    users = cursor.fetchall()
    conn.close()
    return users

def save_trends(chat_id, source, data):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO trends (chat_id, source, data) VALUES (?, ?, ?)',
                   (chat_id, source, json.dumps(data)))
    conn.commit()
    conn.close()


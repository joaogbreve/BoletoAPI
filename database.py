#database.py
import sqlite3
import os

DB_PATH = "boleto.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Retorna dicionários ao invés de tuplas
    return conn

def init_db():
    if not os.path.exists(DB_PATH):
        with open("schema.sql", "r", encoding="utf-8") as f:
            script = f.read()

        conn = get_connection()
        conn.executescript(script)
        conn.commit()
        conn.close()

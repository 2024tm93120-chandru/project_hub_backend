# db.py
import sqlite3

def init_db():
    conn = sqlite3.connect("projecthub.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS requirements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            priority TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS bugs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            severity TEXT,
            steps TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            description TEXT,
            assigned_to TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


def list_requirements():
    return sqlite3.connect("projecthub.db").cursor().execute(
        "SELECT * FROM requirements ORDER BY id DESC"
    ).fetchall()

def list_bugs():
    return sqlite3.connect("projecthub.db").cursor().execute(
        "SELECT * FROM bugs ORDER BY id DESC"
    ).fetchall()

def list_queries():
    return sqlite3.connect("projecthub.db").cursor().execute(
        "SELECT * FROM queries ORDER BY id DESC"
    ).fetchall()

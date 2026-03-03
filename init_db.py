"""
╔══════════════════════════════════════════════════════╗
║   DIGITAL MUSHAYARA — Database Initializer           ║
║   Run ONCE to set up SQLite database                 ║
║   python init_db.py                                  ║
╚══════════════════════════════════════════════════════╝
"""

import sqlite3, json, hashlib, os
from pathlib import Path

DB_PATH = Path(__file__).parent / "mushayara.db"
JSON_PATH = Path(__file__).parent / "shaayaris.json"

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # ── TABLES ──────────────────────────────────────
    c.executescript("""
        CREATE TABLE IF NOT EXISTS shaayaris (
            id          TEXT PRIMARY KEY,
            title       TEXT NOT NULL,
            body        TEXT NOT NULL,
            tags        TEXT DEFAULT '[]',
            status      TEXT DEFAULT 'published',
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            shaayari_id TEXT NOT NULL,
            reaction    TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS comments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            shaayari_id TEXT NOT NULL,
            name        TEXT DEFAULT 'Ek Musafir',
            text        TEXT NOT NULL,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS admin (
            id          INTEGER PRIMARY KEY,
            username    TEXT NOT NULL,
            password    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            type        TEXT NOT NULL,
            shaayari_id TEXT NOT NULL,
            shaayari_title TEXT NOT NULL,
            content     TEXT NOT NULL,
            is_read     INTEGER DEFAULT 0,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # ── MIGRATE SHAAYARIS FROM JSON ─────────────────
    if JSON_PATH.exists():
        shaayaris = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        for s in shaayaris:
            c.execute("""
                INSERT OR IGNORE INTO shaayaris (id, title, body, tags, status)
                VALUES (?, ?, ?, ?, 'published')
            """, (s["id"], s["title"], s["body"], json.dumps(s.get("tags", []))))
        print(f"  ✅ Migrated {len(shaayaris)} shaayaris from JSON")
    else:
        print("  ⚠  No shaayaris.json found — starting with empty database")

    # ── CREATE ADMIN USER ───────────────────────────
    password = input("\n  Set your admin password: ").strip()
    if not password:
        password = "mushayara2024"
        print(f"  Using default password: {password}")

    c.execute("DELETE FROM admin")
    c.execute("INSERT INTO admin (username, password) VALUES (?, ?)",
              ("Nadeem Memon", hash_password(password)))
    print(f"  ✅ Admin created — username: Nadeem Memon")

    conn.commit()
    conn.close()

    print(f"\n  🌙 Database ready at: {DB_PATH}")
    print("  You can now start the server!\n")

if __name__ == "__main__":
    print("\n" + "="*50)
    print("   🌙  Digital Mushayara — DB Init")
    print("="*50 + "\n")
    init()
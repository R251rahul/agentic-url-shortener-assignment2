from __future__ import annotations
import sqlite3
import threading
from datetime import datetime
from pathlib import Path

class SQLiteStore:
    def __init__(self, path: str = "data/app.db"):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self._init()

    def _init(self):
        with self.lock, self.conn:
            self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS urls (
              code TEXT PRIMARY KEY, target_url TEXT NOT NULL,
              created_at TEXT NOT NULL, expires_at TEXT, clicks INTEGER NOT NULL DEFAULT 0,
              last_accessed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS audit_events (
              id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
              run_id TEXT NOT NULL, node_id TEXT, event TEXT NOT NULL,
              actor TEXT NOT NULL, details TEXT NOT NULL
            );
            """)

    def create_url(self, code, target_url, created_at, expires_at=None):
        with self.lock, self.conn:
            self.conn.execute("INSERT INTO urls(code,target_url,created_at,expires_at) VALUES(?,?,?,?)",
                              (code,target_url,created_at.isoformat(),expires_at.isoformat() if expires_at else None))

    def get_url(self, code):
        with self.lock:
            return self.conn.execute("SELECT * FROM urls WHERE code=?", (code,)).fetchone()

    def record_click(self, code, when):
        with self.lock, self.conn:
            self.conn.execute("UPDATE urls SET clicks=clicks+1,last_accessed_at=? WHERE code=?", (when.isoformat(), code))

    def add_audit(self, timestamp, run_id, node_id, event, actor, details_json):
        with self.lock, self.conn:
            self.conn.execute("INSERT INTO audit_events(timestamp,run_id,node_id,event,actor,details) VALUES(?,?,?,?,?,?)",
                              (timestamp.isoformat(),run_id,node_id,event,actor,details_json))

    def audit_for_run(self, run_id):
        with self.lock:
            return self.conn.execute("SELECT * FROM audit_events WHERE run_id=? ORDER BY id", (run_id,)).fetchall()

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


class Database:
    """
    Backend SQLite centralisé.

    La connexion est partagée par les repositories, protégée par un verrou
    réentrant et configurée pour fonctionner avec les workers de scan Qt.
    """

    _instance = None
    _init_lock = threading.Lock()

    DB_PATH = Path.home() / ".neural_storage_analyzer.db"

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self):
        self._lock = threading.RLock()
        self._transaction_depth = 0
        self.conn = sqlite3.connect(
            str(self.DB_PATH),
            check_same_thread=False,
            timeout=30,
        )

        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA temp_store = MEMORY")

        self._create_tables()

    def _create_tables(self):
        with self._lock:
            cur = self.conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    total_size_mb REAL DEFAULT 0,
                    duration_sec REAL DEFAULT 0,
                    scan_type TEXT,
                    status TEXT NOT NULL DEFAULT 'finished'
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_id INTEGER,
                    path TEXT UNIQUE,
                    size_mb REAL,
                    modified TEXT,
                    created TEXT,
                    accessed TEXT,
                    extension TEXT,
                    category TEXT,
                    score REAL,
                    importance TEXT,
                    fingerprint TEXT,
                    sha256 TEXT,
                    is_duplicate INTEGER DEFAULT 0,
                    duplicate_of TEXT,
                    last_seen TEXT,
                    FOREIGN KEY(scan_id) REFERENCES scans(id) ON DELETE CASCADE
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT,
                    action TEXT,
                    timestamp TEXT,
                    metadata TEXT,
                    restored INTEGER DEFAULT 0
                )
            """)

            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_scan ON files(scan_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(sha256)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_fingerprint ON files(fingerprint)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_size ON files(size_mb)")

            # Migration additive pour les bases créées par une version antérieure.
            self._ensure_column("scans", "status", "TEXT NOT NULL DEFAULT 'finished'")
            self.conn.commit()

    def _ensure_column(self, table: str, column: str, definition: str) -> None:
        columns = {
            row[1]
            for row in self.conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in columns:
            self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def execute(self, query: str, params: tuple = ()):
        """Exécute une requête et commit automatiquement hors transaction."""
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(query, params)
            if self._transaction_depth == 0:
                self.conn.commit()
            return cur

    def fetchall(self, query: str, params: tuple = ()):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def fetchone(self, query: str, params: tuple = ()):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Regroupe plusieurs écritures dans une transaction atomique."""
        with self._lock:
            self._transaction_depth += 1
            try:
                yield self.conn
            except Exception:
                self.conn.rollback()
                raise
            else:
                if self._transaction_depth == 1:
                    self.conn.commit()
            finally:
                self._transaction_depth -= 1

    def close(self):
        with self._lock:
            self.conn.commit()
            self.conn.close()
            type(self)._instance = None

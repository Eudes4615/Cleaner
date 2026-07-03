import sqlite3
import threading
from pathlib import Path


class Database:
    """
    SQLite core layer (PURE repository backend foundation)
    - Singleton
    - Thread-safe
    - WAL mode
    - No business logic
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

    # -------------------------
    # INIT
    # -------------------------
    def _init(self):
        self._lock = threading.RLock()

        self.conn = sqlite3.connect(
            str(self.DB_PATH),
            check_same_thread=False,
            timeout=30
        )

        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA temp_store=MEMORY")

        self._create_tables()

    # -------------------------
    # TABLES
    # -------------------------
    def _create_tables(self):
        with self._lock:
            cur = self.conn.cursor()

            # SCANS
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    total_files INTEGER DEFAULT 0,
                    total_size_mb REAL DEFAULT 0,
                    duration_sec REAL DEFAULT 0,
                    scan_type TEXT
                )
            """)

            # FILES
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
                    FOREIGN KEY(scan_id) REFERENCES scans(id)
                )
            """)

            # ACTIONS (rollback)
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

            # INDEXES (performance critique)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_scan ON files(scan_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_hash ON files(sha256)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_fingerprint ON files(fingerprint)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_files_size ON files(size_mb)")

            self.conn.commit()

    # -------------------------
    # SAFE EXECUTION WRAPPER
    # -------------------------
    def execute(self, query: str, params: tuple = ()):
        """
        Thread-safe SQL execution (WRITE)
        """
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(query, params)
            self.conn.commit()
            return cur

    def fetchall(self, query: str, params: tuple = ()):
        """
        Thread-safe SQL execution (READ)
        """
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchall()

    def fetchone(self, query: str, params: tuple = ()):
        """
        Thread-safe single fetch
        """
        with self._lock:
            cur = self.conn.cursor()
            cur.execute(query, params)
            return cur.fetchone()

    # -------------------------
    # CONTEXT TRANSACTION (IMPORTANT)
    # -------------------------
    def transaction(self):
        """
        Usage:
        with db.transaction():
            db.execute(...)
        """
        return self.conn

    def close(self):
        with self._lock:
            self.conn.close()
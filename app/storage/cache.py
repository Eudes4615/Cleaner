import os
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..core.models import FileCategory, FileInfo, Importance


class StorageCache:
    """Cache SQLite pour les scans incrémentaux."""

    DB_PATH = Path.home() / ".neural_storage_cache.db"

    def __init__(self):
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(
            str(self.DB_PATH),
            check_same_thread=False,
            timeout=30,
        )
        self._init_db()

    def _init_db(self):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_cache (
                    path TEXT PRIMARY KEY,
                    size_mb REAL,
                    modified TEXT,
                    score REAL,
                    category TEXT,
                    hash TEXT,
                    last_seen TEXT
                )
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)
            self.conn.commit()

    def save_files(self, files: List[FileInfo]):
        """Sauvegarde les résultats et met à jour la date du scan."""
        now = datetime.now().isoformat()
        with self._lock:
            cursor = self.conn.cursor()
            for file_info in files:
                cursor.execute("""
                    INSERT OR REPLACE INTO scan_cache
                    (path, size_mb, modified, score, category, hash, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    file_info.path,
                    file_info.size_mb,
                    file_info.modified.isoformat(),
                    file_info.score,
                    file_info.category.value,
                    file_info.hash_sha256 or "",
                    now,
                ))

            cursor.execute("""
                INSERT OR REPLACE INTO scan_metadata (key, value)
                VALUES ('last_full_scan', ?)
            """, (now,))
            self.conn.commit()

    def get_last_scan_metadata(self) -> Optional[str]:
        """Retourne la date ISO du dernier scan complet, si elle existe."""
        with self._lock:
            row = self.conn.execute(
                "SELECT value FROM scan_metadata WHERE key = ?",
                ("last_full_scan",),
            ).fetchone()
        return row[0] if row else None

    def get_file_info(self, path: str) -> Optional[FileInfo]:
        """Reconstruit une information de fichier depuis le cache."""
        with self._lock:
            row = self.conn.execute("""
                SELECT path, size_mb, modified, score, category, hash
                FROM scan_cache WHERE path = ?
            """, (path,)).fetchone()

        if not row:
            return None

        modified = datetime.fromisoformat(row[2])
        try:
            stat = Path(path).stat()
            created = datetime.fromtimestamp(stat.st_ctime)
            accessed = datetime.fromtimestamp(stat.st_atime)
        except OSError:
            created = modified
            accessed = modified

        try:
            category = FileCategory(row[4])
        except (ValueError, TypeError):
            category = FileCategory.OTHER

        score = float(row[3] or 0)
        importance = (
            Importance.CRITICAL if score >= 85 else
            Importance.HIGH if score >= 60 else
            Importance.MEDIUM if score >= 30 else
            Importance.LOW if score > 0 else
            Importance.SAFE
        )

        return FileInfo(
            path=row[0],
            size_mb=float(row[1] or 0),
            created=created,
            modified=modified,
            accessed=accessed,
            extension=Path(path).suffix.lower(),
            category=category,
            score=score,
            importance=importance,
            hash_sha256=row[5] or None,
        )

    def get_changed_files(self, current_paths: List[str]) -> List[str]:
        """Retourne les chemins nouveaux ou modifiés depuis le dernier scan."""
        last_scan_value = self.get_last_scan_metadata()
        if not last_scan_value:
            return list(current_paths)

        try:
            last_scan = datetime.fromisoformat(last_scan_value)
        except ValueError:
            return list(current_paths)

        changed = []
        for path in current_paths:
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime > last_scan:
                    changed.append(path)
            except (OSError, FileNotFoundError):
                changed.append(path)
        return changed

    def close(self):
        with self._lock:
            self.conn.commit()
            self.conn.close()

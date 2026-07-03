from typing import Optional, List
from datetime import datetime
from dataclasses import dataclass
from ..core.database import Database

@dataclass
class Scan:
    id: int
    timestamp: str
    total_files: int
    total_size_mb: float
    duration_sec: float
    scan_type: str
    status: str

class ScanRepository:
    def __init__(self):
        self.db = Database()

    def create_scan(self, scan_type: str = "full") -> int:
        with self.db.transaction():
            self.db.execute("""
                INSERT INTO scans (timestamp, total_files, total_size_mb, duration_sec, scan_type, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (datetime.now().isoformat(), 0, 0.0, 0.0, scan_type, "running"))
            return self.db.fetchone("SELECT last_insert_rowid()")[0]

    def finish_scan(self, scan_id: int, total_files: int, total_size_mb: float, duration_sec: float):
        self.db.execute("""
            UPDATE scans
            SET total_files = ?, total_size_mb = ?, duration_sec = ?, status = ?
            WHERE id = ?
        """, (total_files, total_size_mb, duration_sec, "finished", scan_id))

    def cancel_scan(self, scan_id: int):
        self.db.execute("UPDATE scans SET status = ? WHERE id = ?", ("cancelled", scan_id))

    def get_scan(self, scan_id: int) -> Optional[Scan]:
        row = self.db.fetchone("""
            SELECT id, timestamp, total_files, total_size_mb, duration_sec, scan_type, status
            FROM scans WHERE id = ?
        """, (scan_id,))
        if row:
            return Scan(id=row[0], timestamp=row[1], total_files=row[2],
                       total_size_mb=row[3], duration_sec=row[4], scan_type=row[5], status=row[6])
        return None

    def get_latest_scan(self) -> Optional[Scan]:
        row = self.db.fetchone("""
            SELECT id, timestamp, total_files, total_size_mb, duration_sec, scan_type, status
            FROM scans ORDER BY id DESC LIMIT 1
        """)
        if row:
            return Scan(id=row[0], timestamp=row[1], total_files=row[2],
                       total_size_mb=row[3], duration_sec=row[4], scan_type=row[5], status=row[6])
        return None

    def list_scans(self, limit: int = 20) -> List[Scan]:
        rows = self.db.fetchall("""
            SELECT id, timestamp, total_files, total_size_mb, duration_sec, scan_type, status
            FROM scans ORDER BY id DESC LIMIT ?
        """, (limit,))
        return [Scan(id=r[0], timestamp=r[1], total_files=r[2],
                    total_size_mb=r[3], duration_sec=r[4], scan_type=r[5], status=r[6]) for r in rows]

    def delete_scan(self, scan_id: int):
        with self.db.transaction():
            self.db.execute("DELETE FROM files WHERE scan_id = ?", (scan_id,))
            self.db.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
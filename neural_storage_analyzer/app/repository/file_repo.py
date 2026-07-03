from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
from ..core.database import Database
from ..engine.classifier import FileCategory, Importance

@dataclass
class FileRecord:
    path: str
    size_mb: float
    modified: str
    created: str
    accessed: str
    extension: str
    category: FileCategory
    score: float
    importance: Importance
    fingerprint: str
    sha256: str
    is_duplicate: int
    duplicate_of: str
    scan_id: int
    last_seen: str

class FileRepository:
    def __init__(self):
        self.db = Database()
        self._batch_size = 1000

    def bulk_insert(self, scan_id: int, files: List[Dict]):
        if not files:
            return

        values = []
        for f in files:
            values.append((
                scan_id,
                f['path'],
                f['size_mb'],
                f['modified'],
                f['created'],
                f['accessed'],
                f['extension'],
                f['category'].value if hasattr(f['category'], 'value') else str(f['category']),
                f['score'],
                f['importance'].name if hasattr(f['importance'], 'name') else str(f['importance']),
                f.get('fingerprint', ''),
                f.get('sha256', ''),
                0,
                '',
                datetime.now().isoformat()
            ))

        with self.db.transaction():
            for i in range(0, len(values), self._batch_size):
                chunk = values[i:i+self._batch_size]
                self.db.conn.executemany("""
                    INSERT OR REPLACE INTO files (
                        scan_id, path, size_mb, modified, created, accessed,
                        extension, category, score, importance, fingerprint,
                        sha256, is_duplicate, duplicate_of, last_seen
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, chunk)

    def bulk_update(self, files: List[Dict]):
        if not files:
            return

        values = []
        for f in files:
            values.append((
                f.get('is_duplicate', 0),
                f.get('duplicate_of', ''),
                f.get('sha256', ''),
                f.get('fingerprint', ''),
                f['path']
            ))

        with self.db.transaction():
            self.db.conn.executemany("""
                UPDATE files
                SET is_duplicate = ?, duplicate_of = ?, sha256 = ?, fingerprint = ?
                WHERE path = ?
            """, values)

    def find_by_scan(self, scan_id: int, limit: int = 100, offset: int = 0) -> List[FileRecord]:
        rows = self.db.fetchall("""
            SELECT
                path, size_mb, modified, created, accessed, extension,
                category, score, importance, fingerprint, sha256,
                is_duplicate, duplicate_of, scan_id, last_seen
            FROM files WHERE scan_id = ?
            ORDER BY size_mb DESC LIMIT ? OFFSET ?
        """, (scan_id, limit, offset))
        return self._to_records(rows)

    def find_by_hash(self, sha256: str, scan_id: Optional[int] = None) -> List[FileRecord]:
        if scan_id:
            rows = self.db.fetchall("""
                SELECT
                    path, size_mb, modified, created, accessed, extension,
                    category, score, importance, fingerprint, sha256,
                    is_duplicate, duplicate_of, scan_id, last_seen
                FROM files WHERE sha256 = ? AND scan_id = ?
            """, (sha256, scan_id))
        else:
            rows = self.db.fetchall("""
                SELECT
                    path, size_mb, modified, created, accessed, extension,
                    category, score, importance, fingerprint, sha256,
                    is_duplicate, duplicate_of, scan_id, last_seen
                FROM files WHERE sha256 = ?
            """, (sha256,))
        return self._to_records(rows)

    def find_duplicate_groups(self, scan_id: int) -> List[Dict]:
        rows = self.db.fetchall("""
            SELECT
                sha256,
                COUNT(*) as count,
                SUM(size_mb) as total_size
            FROM files
            WHERE scan_id = ? AND sha256 != ''
            GROUP BY sha256
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """, (scan_id,))
        return [{"hash": r[0], "count": r[1], "total_size_mb": r[2]} for r in rows]

    def find_files_by_hash(self, sha256: str) -> List[FileRecord]:
        rows = self.db.fetchall("""
            SELECT
                path, size_mb, modified, created, accessed, extension,
                category, score, importance, fingerprint, sha256,
                is_duplicate, duplicate_of, scan_id, last_seen
            FROM files WHERE sha256 = ?
        """, (sha256,))
        return self._to_records(rows)

    def find_large_files(self, scan_id: int, min_size_mb: float = 50) -> List[FileRecord]:
        rows = self.db.fetchall("""
            SELECT
                path, size_mb, modified, created, accessed, extension,
                category, score, importance, fingerprint, sha256,
                is_duplicate, duplicate_of, scan_id, last_seen
            FROM files
            WHERE scan_id = ? AND size_mb >= ?
            ORDER BY size_mb DESC
        """, (scan_id, min_size_mb))
        return self._to_records(rows)

    def find_by_category(self, scan_id: int, category: str) -> List[FileRecord]:
        rows = self.db.fetchall("""
            SELECT
                path, size_mb, modified, created, accessed, extension,
                category, score, importance, fingerprint, sha256,
                is_duplicate, duplicate_of, scan_id, last_seen
            FROM files WHERE scan_id = ? AND category = ?
        """, (scan_id, category))
        return self._to_records(rows)

    def delete_scan_files(self, scan_id: int):
        self.db.execute("DELETE FROM files WHERE scan_id = ?", (scan_id,))

    def get_count(self, scan_id: int) -> int:
        row = self.db.fetchone("SELECT COUNT(*) FROM files WHERE scan_id = ?", (scan_id,))
        return row[0] if row else 0

    def get_total_size(self, scan_id: int) -> float:
        row = self.db.fetchone("SELECT SUM(size_mb) FROM files WHERE scan_id = ?", (scan_id,))
        return row[0] if row[0] else 0.0

    def _to_records(self, rows) -> List[FileRecord]:
        records = []
        for r in rows:
            # Conversion des enums
            try:
                category = FileCategory(r[6])
            except ValueError:
                category = FileCategory.OTHER
            try:
                importance = Importance[r[8]] if isinstance(r[8], str) else Importance(r[8])
            except (ValueError, KeyError):
                importance = Importance.MEDIUM

            records.append(FileRecord(
                path=r[0], size_mb=r[1], modified=r[2], created=r[3],
                accessed=r[4], extension=r[5], category=category,
                score=r[7], importance=importance, fingerprint=r[9],
                sha256=r[10], is_duplicate=r[11], duplicate_of=r[12],
                scan_id=r[13], last_seen=r[14]
            ))
        return records

    # app/repository/file_repo.py

    def find_files_paginated(self, scan_id: int, last_id: int = 0, limit: int = 1000) -> List[FileRecord]:
        """Paginations par clé (plus scalable que OFFSET)."""
        rows = self.db.fetchall("""
            SELECT
                id, path, size_mb, modified, created, accessed, extension,
                category, score, importance, fingerprint, sha256,
                is_duplicate, duplicate_of, scan_id, last_seen
            FROM files
            WHERE scan_id = ? AND id > ?
            ORDER BY id
            LIMIT ?
        """, (scan_id, last_id, limit))
        return self._to_records_with_id(rows)

    def _to_records_with_id(self, rows) -> List[FileRecord]:
        records = []
        for r in rows:
            # r[0] = id
            records.append(FileRecord(
                id=r[0],
                path=r[1], size_mb=r[2], modified=r[3], created=r[4],
                accessed=r[5], extension=r[6], category=self._to_category(r[7]),
                score=r[8], importance=self._to_importance(r[9]), fingerprint=r[10],
                sha256=r[11], is_duplicate=r[12], duplicate_of=r[13],
                scan_id=r[14], last_seen=r[15]
            ))
        return records 

    def find_by_path(self, scan_id: int, path: str) -> Optional[FileRecord]:
        rows = self.db.fetchall("""
            SELECT
                path, size_mb, modified, created, accessed, extension,
                category, score, importance, fingerprint, sha256,
                is_duplicate, duplicate_of, scan_id, last_seen
            FROM files
            WHERE scan_id = ? AND path = ?
        """, (scan_id, path))
        records = self._to_records(rows)
        return records[0] if records else None

    def find_files_by_fingerprint(self, scan_id: int, fingerprint: str) -> List[FileRecord]:
        rows = self.db.fetchall("""
            SELECT
                path, size_mb, modified, created, accessed, extension,
                category, score, importance, fingerprint, sha256,
                is_duplicate, duplicate_of, scan_id, last_seen
            FROM files
            WHERE scan_id = ? AND fingerprint = ?
        """, (scan_id, fingerprint))
        return self._to_records(rows)

     # app/repository/file_repo.py

    def find_distinct_fingerprints(self, scan_id: int, last_fingerprint: str = "", limit: int = 100) -> List[str]:
        """Retourne une liste de fingerprints distincts (paginer par fingerprint)."""
        rows = self.db.fetchall("""
            SELECT DISTINCT fingerprint
            FROM files
            WHERE scan_id = ? AND fingerprint > ?
            ORDER BY fingerprint
            LIMIT ?
        """, (scan_id, last_fingerprint, limit))
        return [r[0] for r in rows]

    def find_by_fingerprint(self, scan_id: int, fingerprint: str) -> List[FileRecord]:
        """Récupère tous les fichiers d'un fingerprint donné."""
        rows = self.db.fetchall("""
            SELECT
                id, path, size_mb, modified, created, accessed, extension,
                category, score, importance, fingerprint, sha256,
                is_duplicate, duplicate_of, scan_id, last_seen
            FROM files
            WHERE scan_id = ? AND fingerprint = ?
        """, (scan_id, fingerprint))
        return self._to_records_with_id(rows)

    def find_candidates_for_duplicates(self, scan_id: int) -> List[Dict]:
        """
        Retourne les fichiers candidats pour la détection de doublons.
        Fait tout en une seule requête (évite N+1).
        """
        rows = self.db.fetchall("""
            SELECT
                fingerprint,
                GROUP_CONCAT(path) as paths,
                GROUP_CONCAT(size_mb) as sizes,
                GROUP_CONCAT(modified) as modifieds,
                COUNT(*) as count
            FROM files
            WHERE scan_id = ? AND fingerprint != ''
            GROUP BY fingerprint
            HAVING COUNT(*) > 1
        """, (scan_id,))
        results = []
        for row in rows:
            results.append({
                'fingerprint': row[0],
                'paths': row[1].split(','),
                'sizes': [float(x) for x in row[2].split(',')] if row[2] else [],
                'modifieds': row[3].split(',') if row[3] else [],
                'count': row[4]
            })
        return results

   
                    
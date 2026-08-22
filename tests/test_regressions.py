import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from app.core.database import Database
from app.core.models import FileCategory, FileInfo, Importance
from app.engine.classifier import FileCategory as EngineCategory
from app.engine.classifier import Importance as EngineImportance
from app.engine.scanner import ScannerEngine
from app.repository.file_repo import FileRepository
from app.repository.scan_repo import ScanRepository
from app.scanner.incremental import IncrementalScanner
from app.storage.cache import StorageCache


class CleanerRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self._reset_database(self.root / "analyzer.db")

    def tearDown(self):
        if Database._instance is not None:
            Database._instance.close()
            Database._instance = None
        self.temp_dir.cleanup()

    @staticmethod
    def _reset_database(path: Path):
        if Database._instance is not None:
            try:
                Database._instance.close()
            except Exception:
                pass
        Database._instance = None
        Database.DB_PATH = path

    def test_existing_database_gets_scan_status_column(self):
        db_path = self.root / "legacy.db"
        import sqlite3

        connection = sqlite3.connect(db_path)
        connection.execute(
            "CREATE TABLE scans (id INTEGER PRIMARY KEY, timestamp TEXT, "
            "total_files INTEGER, total_size_mb REAL, duration_sec REAL, scan_type TEXT)"
        )
        connection.commit()
        connection.close()

        self._reset_database(db_path)
        db = Database()
        columns = {row[1] for row in db.conn.execute("PRAGMA table_info(scans)")}
        self.assertIn("status", columns)

        scan_repo = ScanRepository()
        scan_id = scan_repo.create_scan("regression")
        scan_repo.finish_scan(scan_id, 1, 2.5, 0.1)
        self.assertEqual(scan_repo.get_scan(scan_id).status, "finished")

    def test_paginated_records_keep_database_id(self):
        scan_id = ScanRepository().create_scan("regression")
        file_repo = FileRepository()
        file_repo.bulk_insert(scan_id, [{
            "path": str(self.root / "document.txt"),
            "size_mb": 1.0,
            "modified": datetime.now().isoformat(),
            "created": datetime.now().isoformat(),
            "accessed": datetime.now().isoformat(),
            "extension": ".txt",
            "category": EngineCategory.DOCUMENT,
            "score": 12.0,
            "importance": EngineImportance.LOW,
            "fingerprint": "fp-1",
            "sha256": "hash-1",
        }])

        records = file_repo.find_files_paginated(scan_id, limit=10)
        self.assertEqual(len(records), 1)
        self.assertIsInstance(records[0].id, int)
        self.assertEqual(records[0].path, str(self.root / "document.txt"))

    def test_scanner_supports_single_file_and_prunes_excluded_dirs(self):
        target = self.root / "target.txt"
        target.write_text("ok", encoding="utf-8")
        excluded = self.root / "Windows" / "hidden.txt"
        excluded.parent.mkdir()
        excluded.write_text("ignore", encoding="utf-8")

        scanned = []
        total = ScannerEngine.scan_multiple(
            [str(target.parent)],
            file_callback=lambda item: scanned.append(item.path),
        )
        self.assertEqual(total, 1)
        self.assertEqual(scanned, [str(target)])

    def test_incremental_cache_contract_is_complete(self):
        cache_path = self.root / "cache.db"
        StorageCache.DB_PATH = cache_path
        scanner = IncrementalScanner()
        file_path = self.root / "cached.txt"
        file_path.write_text("cache", encoding="utf-8")
        now = datetime.now()
        info = FileInfo(
            path=str(file_path),
            size_mb=0.01,
            created=now,
            modified=now,
            accessed=now,
            extension=".txt",
            category=FileCategory.DOCUMENT,
            score=10,
            importance=Importance.LOW,
            hash_sha256="hash-1",
        )
        scanner.cache.save_files([info])

        scanner.load_previous_scan()
        self.assertIsNotNone(scanner.last_scan_time)
        cached = scanner.get_cached_file_info(str(file_path))
        self.assertEqual(cached.hash_sha256, "hash-1")
        new_file = self.root / "new.txt"
        new_file.write_text("new", encoding="utf-8")
        future = (datetime.now() + timedelta(seconds=2)).timestamp()
        import os
        os.utime(new_file, (future, future))
        files_to_scan = scanner.get_files_to_scan(str(self.root))
        self.assertNotIn(str(file_path), files_to_scan)
        self.assertIn(str(new_file), files_to_scan)
        scanner.close()


if __name__ == "__main__":
    unittest.main()

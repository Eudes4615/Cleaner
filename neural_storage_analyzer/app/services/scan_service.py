import os
import time
from pathlib import Path
from typing import List, Optional
from PyQt6.QtCore import QObject, pyqtSignal

from ..core.scan_context import ScanContext
from ..engine.scanner import ScannerEngine
from ..engine.classifier import ClassifierEngine
from ..engine.hasher import HasherEngine
from ..repository.scan_repo import ScanRepository
from ..repository.file_repo import FileRepository

class ScanService(QObject):
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    batch_saved = pyqtSignal(int)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)
    duplicate_scan_requested = pyqtSignal(int)

    BATCH_SIZE = 1000

    def __init__(self):
        super().__init__()
        self.scan_repo = ScanRepository()
        self.file_repo = FileRepository()
        self.context: Optional[ScanContext] = None

    def start_scan(self, paths: List[str], min_size_mb: float = 0,
                   check_duplicates: bool = True, scan_type: str = "full"):
        if self.context and self.context.is_running:
            self.error.emit("Un scan est déjà en cours.")
            return
        try:
            self._run_scan(paths, min_size_mb, check_duplicates, scan_type)
        except Exception as e:
            self.error.emit(str(e))
            if self.context:
                self.scan_repo.cancel_scan(self.context.scan_id)
            raise
        finally:
            if self.context:
                with self.context.lock:
                    self.context.is_running = False

    def cancel_scan(self):
        if self.context:
            self.context.cancel()
            self.status.emit("⏹️ Annulation demandée...")

    def get_status(self) -> dict:
        if not self.context:
            return {"running": False}
        with self.context.lock:
            return {
                "running": self.context.is_running,
                "cancelled": self.context.cancelled,
                "processed": self.context.processed_files,
                "total": self.context.total_files,
                "scan_id": self.context.scan_id,
            }

    def _run_scan(self, paths: List[str], min_size_mb: float,
                  check_duplicates: bool, scan_type: str):
        start_time = time.time()
        scan_id = self.scan_repo.create_scan(scan_type)
        self.context = ScanContext(scan_id=scan_id)
        self.status.emit(f"🔍 Scan #{scan_id} démarré sur {len(paths)} dossier(s)")

        total_size_mb = 0.0
        processed_count = 0
        batch_buffer = []

        def stop_flag():
            return self.context.cancelled

        # Comptage rapide
        total = 0
        for path in paths:
            if not os.path.exists(path):
                continue
            try:
                for root, dirs, files in os.walk(path):
                    root_path = Path(root)
                    if ScannerEngine._is_excluded(root_path):
                        dirs[:] = []
                        continue
                    dirs[:] = [d for d in dirs if not ScannerEngine._is_excluded(root_path / d)]
                    total += len(files)
            except PermissionError:
                continue

        with self.context.lock:
            self.context.total_files = total

        self.status.emit(f"📊 {total} fichiers à analyser")

        def file_callback(file_stat):
            nonlocal processed_count, total_size_mb, batch_buffer
            if self.context.cancelled:
                return

            processed_count += 1
            with self.context.lock:
                self.context.processed_files = processed_count

            analysis = ClassifierEngine.analyze(
                file_stat.path, file_stat.size_mb,
                file_stat.modified, file_stat.accessed
            )

            if check_duplicates:
                hash_result = HasherEngine.smart_hash(file_stat.path, file_stat.size_mb)
            else:
                hash_result = {"fingerprint": "", "hash": "", "level": "disabled"}

            file_data = {
                "path": file_stat.path,
                "size_mb": file_stat.size_mb,
                "modified": file_stat.modified,
                "created": file_stat.created,
                "accessed": file_stat.accessed,
                "extension": file_stat.extension,
                "category": analysis["category"],
                "score": analysis["score"],
                "importance": analysis["importance"],
                "fingerprint": hash_result["fingerprint"],
                "sha256": hash_result["hash"],
            }

            total_size_mb += file_stat.size_mb
            batch_buffer.append(file_data)

            if len(batch_buffer) >= self.BATCH_SIZE:
                self.file_repo.bulk_insert(scan_id, batch_buffer)
                self.batch_saved.emit(len(batch_buffer))
                self.progress.emit(processed_count, total)
                batch_buffer.clear()

            if processed_count % 100 == 0:
                self.progress.emit(processed_count, total)

        scanner = ScannerEngine()
        scanner.scan_multiple(paths, min_size_mb, file_callback, stop_flag)

        if batch_buffer:
            self.file_repo.bulk_insert(scan_id, batch_buffer)
            self.batch_saved.emit(len(batch_buffer))
            batch_buffer.clear()

        duration = time.time() - start_time
        total_files = self.file_repo.get_count(scan_id)
        total_size = self.file_repo.get_total_size(scan_id)

        if self.context.cancelled:
            self.scan_repo.cancel_scan(scan_id)
            self.status.emit("⏹️ Scan annulé.")
        else:
            self.scan_repo.finish_scan(scan_id, total_files, total_size, duration)
            self.status.emit(f"✅ Scan #{scan_id} terminé en {duration:.1f}s")

        if check_duplicates and not self.context.cancelled:
            self.duplicate_scan_requested.emit(scan_id)

        self.finished.emit(scan_id)
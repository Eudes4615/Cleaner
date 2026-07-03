# app/services/duplicate_service.py

import time
from typing import List, Optional
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal

from ..engine.hasher import HasherEngine
from ..repository.file_repo import FileRepository, FileRecord

@dataclass
class DuplicateGroup:
    hash: str
    files: List[FileRecord]
    wasted_space_mb: float
    keep: Optional[FileRecord] = None

class DuplicateService(QObject):
    progress = pyqtSignal(int, int)
    status = pyqtSignal(str)
    group_found = pyqtSignal(object)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.file_repo = FileRepository()
        self._is_running = False
        self._cancelled = False

    def start(self, scan_id: int):
        if self._is_running:
            self.error.emit("Déjà en cours.")
            return

        self._is_running = True
        self._cancelled = False
        self.status.emit(f"🔐 Doublons scan #{scan_id}")

        try:
            self._run(scan_id)
        except Exception as e:
            self.error.emit(str(e))
            raise
        finally:
            self._is_running = False

    def cancel(self):
        self._cancelled = True
        self.status.emit("⏹️ Annulation")

    def _run(self, scan_id: int):
        last_fingerprint = ""
        limit = 50  # nombre de fingerprints par lot

        while True:
            fingerprints = self.file_repo.find_distinct_fingerprints(
                scan_id, last_fingerprint, limit
            )
            if not fingerprints:
                break

            for fp in fingerprints:
                if self._cancelled:
                    return

            # Récupère tous les fichiers de ce fingerprint (UNIQUEMENT 1 requête)
                files = self.file_repo.find_by_fingerprint(scan_id, fp)

                if len(files) > 1:
                    # Traiter le groupe
                    self._process_group(files)

                last_fingerprint = fp

            self.progress.emit(len(fingerprints), total)  # progression par groupe
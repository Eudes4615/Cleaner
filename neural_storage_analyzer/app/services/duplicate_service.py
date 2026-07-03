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
        start = time.time()
        last_fingerprint = ""
        limit = 50
        total_groups = 0

        while True:
            if self._cancelled:
                return

            fingerprints = self.file_repo.find_distinct_fingerprints(
                scan_id, last_fingerprint, limit
            )
            if not fingerprints:
                break

            for fp in fingerprints:
                if self._cancelled:
                    return

                files = self.file_repo.find_by_fingerprint(scan_id, fp)
                if len(files) > 1:
                    # Calcul des SHA256 manquants
                    sha_updates = []
                    for rec in files:
                        if not rec.sha256:
                            sha = HasherEngine.sha256(rec.path)
                            sha_updates.append({"path": rec.path, "sha256": sha})
                    if sha_updates:
                        self.file_repo.bulk_update(sha_updates)

                    # Recharger avec les SHA256
                    files = self.file_repo.find_by_fingerprint(scan_id, fp)

                    # Regrouper par SHA256
                    sha_groups = {}
                    for rec in files:
                        if rec.sha256:
                            sha_groups.setdefault(rec.sha256, []).append(rec)

                    for sha, recs in sha_groups.items():
                        if len(recs) > 1:
                            total_size = sum(r.size_mb for r in recs)
                            wasted = total_size - recs[0].size_mb
                            keep = max(recs, key=lambda r: r.modified)
                            group = DuplicateGroup(
                                hash=sha,
                                files=recs,
                                wasted_space_mb=round(wasted, 2),
                                keep=keep
                            )
                            total_groups += 1
                            self.group_found.emit(group)

                            updates = []
                            for rec in recs:
                                if rec.path != keep.path:
                                    updates.append({
                                        "path": rec.path,
                                        "is_duplicate": 1,
                                        "duplicate_of": keep.path,
                                        "sha256": sha,
                                    })
                            if updates:
                                self.file_repo.bulk_update(updates)

                last_fingerprint = fp

            self.progress.emit(total_groups, 0)

        elapsed = time.time() - start
        self.status.emit(f"✅ {total_groups} groupes en {elapsed:.1f}s")
        self.finished.emit(scan_id)
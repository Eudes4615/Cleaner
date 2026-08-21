import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from ..storage.cache import StorageCache


class IncrementalScanner:
    """Sélectionne uniquement les fichiers nouveaux ou modifiés."""

    def __init__(self):
        self.cache = StorageCache()
        self.last_scan_time: Optional[datetime] = None
        self.scanned_files: Set[str] = set()

    def load_previous_scan(self):
        """Charge la date du dernier scan depuis le cache."""
        result = self.cache.get_last_scan_metadata()
        if not result:
            self.last_scan_time = None
            return
        try:
            self.last_scan_time = datetime.fromisoformat(result)
        except ValueError:
            self.last_scan_time = None

    def get_files_to_scan(self, directory: str) -> List[str]:
        """Retourne les fichiers nouveaux ou modifiés depuis le dernier scan."""
        self.load_previous_scan()
        self.scanned_files.clear()

        files_to_scan = []
        root_path = Path(directory).expanduser()
        if not root_path.exists():
            return files_to_scan

        candidates = [root_path] if root_path.is_file() else (
            Path(root) / name
            for root, _, names in os.walk(root_path)
            for name in names
        )

        for path in candidates:
            try:
                if not path.is_file():
                    continue
                modified = datetime.fromtimestamp(path.stat().st_mtime)
                if self.last_scan_time is None or modified > self.last_scan_time:
                    files_to_scan.append(str(path))
                else:
                    self.scanned_files.add(str(path))
            except (PermissionError, OSError, FileNotFoundError):
                continue

        return files_to_scan

    def get_cached_file_info(self, path: str):
        """Récupère les informations d’un fichier depuis le cache."""
        return self.cache.get_file_info(path)

    def mark_scan_complete(self, files: List):
        """Persiste les fichiers analysés et clôture le cycle de cache."""
        self.cache.save_files(files)
        self.load_previous_scan()

    def get_scan_stats(self) -> dict:
        """Retourne les statistiques du dernier passage incrémental."""
        return {
            "cached_files": len(self.scanned_files),
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "cache_db_path": str(self.cache.DB_PATH),
        }

    def close(self):
        self.cache.close()

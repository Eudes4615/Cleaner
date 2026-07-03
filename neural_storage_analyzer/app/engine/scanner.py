import os
from pathlib import Path
from typing import Optional, Callable


class FileStat:
    def __init__(self, path, size_mb, created, modified, accessed, extension):
        self.path = path
        self.size_mb = size_mb
        self.created = created
        self.modified = modified
        self.accessed = accessed
        self.extension = extension


class ScannerEngine:

    SYSTEM_DIRS = {
        "windows", "program files", "system32", "boot"
    }

    @classmethod
    def _is_excluded(cls, path: Path) -> bool:
        parts = [p.lower() for p in path.parts]
        return any(p in cls.SYSTEM_DIRS for p in parts)

    @classmethod
    def scan_multiple(
        cls,
        paths: list[str],
        min_size_mb: float = 0,
        file_callback: Optional[Callable[[FileStat], None]] = None,
        stop_flag: Optional[Callable[[], bool]] = None
    ) -> int:

        total = 0

        for base in paths:
            if not os.path.exists(base):
                continue

            for root, dirs, files in os.walk(base):
                root_path = Path(root)

                if cls._is_excluded(root_path):
                    dirs[:] = []
                    continue

                for name in files:
                    if stop_flag and stop_flag():
                        return total

                    file_path = root_path / name

                    try:
                        stat = file_path.stat()
                        size_mb = stat.st_size / (1024 * 1024)

                        if size_mb < min_size_mb:
                            continue

                        total += 1

                        if file_callback:
                            file_callback(FileStat(
                                str(file_path),
                                size_mb,
                                stat.st_ctime,
                                stat.st_mtime,
                                stat.st_atime,
                                file_path.suffix.lower()
                            ))

                    except Exception:
                        continue

        return total
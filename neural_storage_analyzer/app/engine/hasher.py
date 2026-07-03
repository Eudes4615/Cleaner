import hashlib
from pathlib import Path
from typing import Optional


class HasherEngine:
    """
    Pure hashing engine.
    - No DB
    - No IO orchestration
    - Stateless
    """

    CHUNK_SIZE = 1024 * 1024  # 1MB

    # -----------------------------
    # 1. FINGERPRINT (ULTRA FAST)
    # -----------------------------
    @staticmethod
    def fingerprint(path: str, size: int) -> str:
        """
        Fast pre-hash used for grouping candidates.
        - file size
        - first 1MB
        - last 1MB
        """
        try:
            with open(path, "rb") as f:
                head = f.read(HasherEngine.CHUNK_SIZE)

                if size > HasherEngine.CHUNK_SIZE:
                    f.seek(max(0, size - HasherEngine.CHUNK_SIZE))
                    tail = f.read(HasherEngine.CHUNK_SIZE)
                else:
                    tail = head

            return hashlib.md5(
                head + tail + str(size).encode()
            ).hexdigest()

        except (PermissionError, OSError, FileNotFoundError):
            return ""

    # -----------------------------
    # 2. QUICK HASH (MEDIUM LEVEL)
    # -----------------------------
    @staticmethod
    def quick_hash(path: str) -> str:
        """
        Faster than SHA-256:
        - sample chunks only (start + middle + end)
        """
        try:
            file_size = Path(path).stat().st_size

            with open(path, "rb") as f:
                head = f.read(HasherEngine.CHUNK_SIZE)

                if file_size > 2 * HasherEngine.CHUNK_SIZE:
                    f.seek(file_size // 2)
                    middle = f.read(HasherEngine.CHUNK_SIZE)
                else:
                    middle = b""

                if file_size > HasherEngine.CHUNK_SIZE:
                    f.seek(max(0, file_size - HasherEngine.CHUNK_SIZE))
                    tail = f.read(HasherEngine.CHUNK_SIZE)
                else:
                    tail = head

            return hashlib.sha1(head + middle + tail).hexdigest()

        except (PermissionError, OSError, FileNotFoundError):
            return ""

    # -----------------------------
    # 3. FULL SHA-256 (TRUTH)
    # -----------------------------
    @staticmethod
    def sha256(path: str) -> str:
        """
        Full cryptographic hash (slow but exact).
        """
        try:
            h = hashlib.sha256()

            with open(path, "rb") as f:
                while True:
                    chunk = f.read(HasherEngine.CHUNK_SIZE)
                    if not chunk:
                        break
                    h.update(chunk)

            return h.hexdigest()

        except (PermissionError, OSError, FileNotFoundError):
            return ""

    # -----------------------------
    # 4. SMART HASH PIPELINE
    # -----------------------------
    @classmethod
    def smart_hash(cls, path: str, size_mb: float) -> dict:
        """
        Adaptive hashing strategy.

        Returns:
        {
            "fingerprint": str,
            "hash": str,
            "level": str
        }
        """

        try:
            size_bytes = int(size_mb * 1024 * 1024)

            fp = cls.fingerprint(path, size_bytes)

            # ultra small files → no need SHA
            if size_mb < 50:
                return {
                    "fingerprint": fp,
                    "hash": fp,
                    "level": "fingerprint"
                }

            # medium files → quick hash
            if size_mb < 200:
                return {
                    "fingerprint": fp,
                    "hash": cls.quick_hash(path),
                    "level": "quick"
                }

            # large files → full SHA-256
            return {
                "fingerprint": fp,
                "hash": cls.sha256(path),
                "level": "sha256"
            }

        except Exception:
            return {
                "fingerprint": "",
                "hash": "",
                "level": "error"
            }
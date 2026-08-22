from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engine.classifier import ClassifierEngine, FileCategory
from app.engine.hasher import HasherEngine


def main() -> None:
    assert ClassifierEngine.classify("C:/Windows/System32/kernel.dll", 1) == FileCategory.SYSTEM
    assert ClassifierEngine.classify("c:/windows/system32/kernel.dll", 1) == FileCategory.SYSTEM
    assert ClassifierEngine.classify("/tmp/sample.tmp", 1) == FileCategory.CACHE
    assert ClassifierEngine.classify("/tmp/report.pdf", 1) == FileCategory.DOCUMENT

    with TemporaryDirectory(prefix="cleaner-ci-") as dirname:
        path = Path(dirname) / "sample.bin"
        payload = b"cleaner-ci-smoke"
        path.write_bytes(payload)
        digest = HasherEngine.sha256(str(path))
        assert digest == hashlib.sha256(payload).hexdigest()
        assert HasherEngine.fingerprint(str(path), path.stat().st_size)
        assert HasherEngine.smart_hash(str(path), path.stat().st_size / 1024 / 1024)["hash"]

    print("Cleaner smoke tests: PASS")


if __name__ == "__main__":
    main()

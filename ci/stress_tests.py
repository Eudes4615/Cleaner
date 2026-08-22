from __future__ import annotations

import hashlib
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.engine.classifier import ClassifierEngine, FileCategory
from app.engine.hasher import HasherEngine


def run_case(case_id: int) -> None:
    extension, expected = (
        (".tmp", FileCategory.CACHE),
        (".pdf", FileCategory.DOCUMENT),
        (".zip", FileCategory.ARCHIVE),
        (".jpg", FileCategory.MEDIA),
    )[case_id % 4]
    path_label = f"/tmp/cleaner-ci-{case_id:06d}{extension}"
    with TemporaryDirectory(prefix="cleaner-stress-") as dirname:
        path = Path(dirname) / f"case-{case_id:06d}.bin"
        payload = f"cleaner-case-{case_id}".encode() * 32
        path.write_bytes(payload)
        assert ClassifierEngine.classify(path_label, path.stat().st_size / 1024 / 1024) == expected
        assert HasherEngine.sha256(str(path)) == hashlib.sha256(payload).hexdigest()
        assert HasherEngine.smart_hash(str(path), path.stat().st_size / 1024 / 1024)["hash"]


def main() -> None:
    iterations = int(os.environ.get("STRESS_ITERATIONS", "100"))
    workers = int(os.environ.get("STRESS_WORKERS", "4"))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        list(pool.map(run_case, range(iterations)))
    print(f"Cleaner stress tests: PASS ({iterations} cases, {workers} workers)")


if __name__ == "__main__":
    main()

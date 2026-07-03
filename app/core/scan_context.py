import threading
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ScanContext:
    """
    Shared execution context for a single scan session
    """

    scan_id: int
    timestamp: datetime = field(default_factory=datetime.now)

    # synchronization
    lock: threading.RLock = field(default_factory=threading.RLock)

    # runtime counters
    processed_files: int = 0
    total_files: int = 0

    # state flags
    is_running: bool = True
    cancelled: bool = False

    # duplicate cache (important fix)
    fingerprint_map: dict = field(default_factory=dict)

    def increment(self):
        with self.lock:
            self.processed_files += 1

    def cancel(self):
        with self.lock:
            self.cancelled = True
            self.is_running = False
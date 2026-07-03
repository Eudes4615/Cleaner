from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

class FileCategory(Enum):
    CACHE = "cache"
    MEDIA = "media"
    INSTALLER = "installer"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    SYSTEM = "system"
    DUPLICATE = "duplicate"
    OTHER = "other"

class Importance(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    SAFE = 1

@dataclass
class FileInfo:
    path: str
    size_mb: float
    created: datetime
    modified: datetime
    accessed: datetime
    extension: str
    category: FileCategory
    score: float
    importance: Importance
    is_duplicate: bool = False          # ✅ valeur par défaut
    duplicate_of: Optional[str] = None  # ✅ valeur par défaut
    hash_sha256: Optional[str] = None   # ✅ valeur par défaut
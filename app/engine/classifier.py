from pathlib import Path
from datetime import datetime
from typing import List, Callable
from enum import Enum

from ..core.config import Config


class FileCategory(Enum):
    CACHE = "cache"
    MEDIA = "media"
    INSTALLER = "installer"
    DOCUMENT = "document"
    ARCHIVE = "archive"
    SYSTEM = "system"
    OTHER = "other"


class Importance(Enum):
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    SAFE = 1


class ClassificationRule:
    def __init__(self, name: str, category: FileCategory, condition: Callable[[Path, float], bool]):
        self.name = name
        self.category = category
        self.condition = condition


class ClassifierEngine:
    _rules: List[ClassificationRule] = []

    @classmethod
    def _init_rules(cls):
        if cls._rules:
            return

        cls._rules = [
            ClassificationRule("cache_ext", FileCategory.CACHE,
                lambda p, s: p.suffix.lower() in {'.tmp', '.temp', '.cache', '.log', '.bak'}),

            ClassificationRule("installer", FileCategory.INSTALLER,
                lambda p, s: p.suffix.lower() in {'.exe', '.msi', '.apk', '.dmg'}),

            ClassificationRule("media", FileCategory.MEDIA,
                lambda p, s: p.suffix.lower() in {'.mp4', '.mp3', '.mkv', '.jpg', '.png'}),

            ClassificationRule("archive", FileCategory.ARCHIVE,
                lambda p, s: p.suffix.lower() in {'.zip', '.rar', '.7z', '.tar'}),

            ClassificationRule("document", FileCategory.DOCUMENT,
                lambda p, s: p.suffix.lower() in {'.pdf', '.docx', '.txt', '.csv'}),

            ClassificationRule("system", FileCategory.SYSTEM,
                lambda p, s: 'windows' in p.parts or 'system32' in p.parts),
        ]

    @classmethod
    def classify(cls, path: str, size_mb: float) -> FileCategory:
        cls._init_rules()
        p = Path(path)

        for rule in cls._rules:
            if rule.condition(p, size_mb):
                return rule.category

        return FileCategory.OTHER

    @classmethod
    def calculate_risk_score(
        cls,
        path: str,
        size_mb: float,
        modified: datetime,
        accessed: datetime,
        category: FileCategory
    ) -> float:

        age_days = (datetime.now() - modified).days

        score = (
            min(size_mb * 2, 100) +
            min(age_days / 10, 100)
        )

        if category == FileCategory.SYSTEM:
            score += 40

        return max(0, min(100, round(score, 2)))

    @classmethod
    def get_importance(cls, score: float) -> Importance:
        if score >= 85:
            return Importance.CRITICAL
        if score >= 60:
            return Importance.HIGH
        if score >= 30:
            return Importance.MEDIUM
        if score > 0:
            return Importance.LOW
        return Importance.SAFE

    @classmethod
    def analyze(cls, path: str, size_mb: float, modified: datetime, accessed: datetime):
        category = cls.classify(path, size_mb)
        score = cls.calculate_risk_score(path, size_mb, modified, accessed, category)
        importance = cls.get_importance(score)

        return {
            "category": category,
            "score": score,
            "importance": importance,
        }
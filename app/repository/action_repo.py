from typing import List, Optional
from datetime import datetime
from dataclasses import dataclass
from ..core.database import Database

@dataclass
class Action:
    id: int
    path: str
    action: str
    timestamp: str
    metadata: str
    restored: int

class ActionRepository:
    def __init__(self):
        self.db = Database()

    def log_action(self, path: str, action: str, metadata: str = ""):
        self.db.execute("""
            INSERT INTO actions (path, action, timestamp, metadata, restored)
            VALUES (?, ?, ?, ?, ?)
        """, (path, action, datetime.now().isoformat(), metadata, 0))

    def undo_action(self, action_id: int):
        self.db.execute("UPDATE actions SET restored = 1 WHERE id = ?", (action_id,))

    def list_actions(self, restored: Optional[int] = 0, limit: int = 100) -> List[Action]:
        if restored is not None:
            rows = self.db.fetchall("""
                SELECT id, path, action, timestamp, metadata, restored
                FROM actions WHERE restored = ? ORDER BY id DESC LIMIT ?
            """, (restored, limit))
        else:
            rows = self.db.fetchall("""
                SELECT id, path, action, timestamp, metadata, restored
                FROM actions ORDER BY id DESC LIMIT ?
            """, (limit,))
        return [Action(id=r[0], path=r[1], action=r[2], timestamp=r[3], metadata=r[4], restored=r[5]) for r in rows]

    def purge_old_actions(self, days: int = 30):
        self.db.execute("""
            DELETE FROM actions
            WHERE restored = 1 AND datetime(timestamp) < datetime('now', ?)
        """, (f'-{days} days',))
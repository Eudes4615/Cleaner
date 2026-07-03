import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from ..core.models import FileInfo

class StorageCache:
    """Cache SQLite pour les scans incrémentaux"""
    
    DB_PATH = Path.home() / '.neural_storage_cache.db'
    
    def __init__(self):
        self._init_db()
    
    def _init_db(self):
        """Initialise la base de données"""
        self.conn = sqlite3.connect(str(self.DB_PATH))
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_cache (
                path TEXT PRIMARY KEY,
                size_mb REAL,
                modified TEXT,
                score REAL,
                category TEXT,
                hash TEXT,
                last_seen TEXT
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scan_metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()
    
    def save_files(self, files: List[FileInfo]):
        """Sauvegarde les résultats du scan"""
        cursor = self.conn.cursor()
        now = datetime.now().isoformat()
        
        for f in files:
            cursor.execute('''
                INSERT OR REPLACE INTO scan_cache 
                (path, size_mb, modified, score, category, hash, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                f.path,
                f.size_mb,
                f.modified.isoformat(),
                f.score,
                f.category.value,
                f.hash_sha256,
                now
            ))
        
        # Mise à jour de la métadonnée de dernière analyse
        cursor.execute('''
            INSERT OR REPLACE INTO scan_metadata (key, value)
            VALUES ('last_full_scan', ?)
        ''', (now,))
        
        self.conn.commit()
    
    def get_changed_files(self, current_paths: List[str]) -> List[str]:
        """Retourne les chemins qui ont changé depuis le dernier scan"""
        cursor = self.conn.cursor()
        
        # Récupérer la date du dernier scan
        cursor.execute('SELECT value FROM scan_metadata WHERE key = "last_full_scan"')
        row = cursor.fetchone()
        if not row:
            return current_paths  # Premier scan => tout scanner
        
        last_scan = datetime.fromisoformat(row[0])
        
        changed = []
        for path in current_paths:
            try:
                import os
                mtime = datetime.fromtimestamp(os.path.getmtime(path))
                if mtime > last_scan:
                    changed.append(path)
            except (OSError, FileNotFoundError):
                changed.append(path)  # Fichier supprimé ou inaccessible
        
        return changed
    
    def close(self):
        self.conn.close()
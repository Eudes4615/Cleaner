import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set
from ..storage.cache import StorageCache

class IncrementalScanner:
    """Scan incrémental : ne scanne que les fichiers modifiés depuis le dernier scan"""
    
    def __init__(self):
        self.cache = StorageCache()
        self.last_scan_time: Optional[datetime] = None
        self.scanned_files: Set[str] = set()
    
    def load_previous_scan(self):
        """Charge les infos du dernier scan depuis le cache"""
        result = self.cache.get_last_scan_metadata()
        if result:
            self.last_scan_time = datetime.fromisoformat(result)
    
    def get_files_to_scan(self, directory: str) -> List[str]:
        """Retourne la liste des fichiers à scanner (modifiés ou nouveaux)"""
        self.load_previous_scan()
        
        files_to_scan = []
        total_files = 0
        
        try:
            for root, _, files in os.walk(directory):
                for name in files:
                    total_files += 1
                    path = os.path.join(root, name)
                    
                    try:
                        mtime = os.path.getmtime(path)
                        mod_time = datetime.fromtimestamp(mtime)
                        
                        # Si pas de précédent scan, tout scanner
                        if self.last_scan_time is None:
                            files_to_scan.append(path)
                        # Sinon, ne scanner que les fichiers modifiés
                        elif mod_time > self.last_scan_time:
                            files_to_scan.append(path)
                        # Sinon, on prend depuis le cache
                        else:
                            self.scanned_files.add(path)
                            
                    except (PermissionError, OSError):
                        continue
                        
        except PermissionError:
            pass
        
        return files_to_scan
    
    def get_cached_file_info(self, path: str):
        """Récupère les infos d'un fichier depuis le cache"""
        return self.cache.get_file_info(path)
    
    def mark_scan_complete(self, files: List):
        """Marque la fin du scan et met à jour le cache"""
        from ..core.models import FileInfo
        self.cache.save_files(files)
        
    def get_scan_stats(self) -> dict:
        """Retourne des stats sur le scan incrémental"""
        cached_count = len(self.scanned_files)
        return {
            "cached_files": cached_count,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "cache_db_path": str(self.cache.DB_PATH)
        }
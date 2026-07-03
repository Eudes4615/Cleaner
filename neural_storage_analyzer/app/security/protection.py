import os
from pathlib import Path

class SecurityManager:
    """Protection contre la suppression de fichiers système critiques"""
    
    CRITICAL_PATHS = [
        'C:/Windows',
        'C:/Program Files',
        'C:/Program Files (x86)',
        'C:/System32',
        '/bin',
        '/boot',
        '/dev',
        '/etc',
        '/lib',
        '/proc',
        '/root',
        '/sbin',
        '/sys',
        '/usr',
        '/System',
        '/Library',
        # Dossiers applicatifs
        '/Applications',
        '/usr/local/bin'
    ]
    
    PROTECTED_EXTENSIONS = {'.dll', '.sys', '.ini', '.cfg', '.conf', '.log'}  # logs système
    
    def is_safe(self, path: str) -> bool:
        """Vérifie si le fichier peut être supprimé sans risque"""
        path_lower = path.lower().replace('\\', '/')
        
        # 1. Vérifier les chemins critiques
        for critical in self.CRITICAL_PATHS:
            if path_lower.startswith(critical.lower().replace('\\', '/')):
                return False
        
        # 2. Vérifier les extensions protégées
        ext = Path(path).suffix.lower()
        if ext in self.PROTECTED_EXTENSIONS:
            # Autoriser uniquement dans les dossiers utilisateur
            if 'appdata' not in path_lower and 'user' not in path_lower:
                return False
        
        # 3. Vérifier les fichiers en cours d'utilisation (Windows)
        try:
            import psutil
            for proc in psutil.process_iter(['open_files']):
                try:
                    for file in proc.info['open_files'] or []:
                        if file.path == path:
                            return False  # Fichier ouvert => ne pas supprimer
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            pass  # psutil non installé, on ignore
        
        return True
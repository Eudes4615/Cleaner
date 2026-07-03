from pathlib import Path
from typing import List
from ..core.models import FileInfo, FileCategory

class IntelligentClassifier:
    """Classification intelligente des fichiers"""
    
    # Dossiers connus comme "junk"
    JUNK_DIRS = {
        'node_modules', 'vendor', '.git', '__pycache__', '.pytest_cache',
        '.vscode', '.idea', '.vs', 'bin', 'obj', 'target', 'build',
        'dist', 'lib', 'include', 'CMakeFiles', '.gradle', '.mvn'
    }
    
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
    
    def classify_file(self, file_info: FileInfo) -> dict:
        """Classification enrichie d'un fichier"""
        path = file_info.path
        path_parts = Path(path).parts
        category = file_info.category
        
        # Détection des dossiers junk
        is_junk = any(junk in path_parts for junk in self.JUNK_DIRS)
        
        # Détection des caches de navigateurs
        is_browser_cache = any(x in path.lower() for x in [
            'cache', 'browser', 'chrome', 'firefox', 'edge', 'safari'
        ]) and 'cache' in path.lower()
        
        # Détection des fichiers temporaires de développement
        is_dev_temp = any(x in path.lower() for x in [
            'temp', 'tmp', 'log', 'debug'
        ]) and any(x in path_parts for x in ['src', 'app', 'lib', 'include'])
        
        return {
            'category': category.value,
            'is_junk': is_junk,
            'is_browser_cache': is_browser_cache,
            'is_dev_temp': is_dev_temp,
            'score_boost': self._get_boost(category, is_junk, is_browser_cache, is_dev_temp)
        }
    
    def _get_boost(self, category: FileCategory, is_junk: bool, 
                   is_browser_cache: bool, is_dev_temp: bool) -> float:
        """Boost ou penalty du score IA"""
        boost = 0.0
        
        # Les caches et junk sont plus supprimables
        if category == FileCategory.CACHE:
            boost = -15.0
        if is_junk:
            boost = -10.0
        if is_browser_cache:
            boost = -20.0
        if is_dev_temp:
            boost = -10.0
            
        # Les fichiers système sont moins supprimables
        if category == FileCategory.SYSTEM:
            boost = +20.0
            
        return boost
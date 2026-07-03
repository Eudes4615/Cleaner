import math
from datetime import datetime, timedelta
from pathlib import Path
from .models import FileInfo, FileCategory, Importance

class ScoringEngine:
    """Moteur de score IA pour chaque fichier"""
    
    # Poids des critères
    WEIGHT_SIZE = 0.25
    WEIGHT_AGE = 0.20
    WEIGHT_TYPE = 0.20
    WEIGHT_USAGE = 0.15
    WEIGHT_LOCATION = 0.20
    
    # Seuils
    MAX_SIZE_MB = 10000  # 10 Go -> score max
    MAX_AGE_DAYS = 365   # 1 an -> score max
    
    def calculate_score(self, file_info: FileInfo) -> float:
        """Calcule le score final (0 = supprimable, 100 = critique)"""
        
        scores = {
            'size': self._score_size(file_info.size_mb),
            'age': self._score_age(file_info.modified),
            'type': self._score_type(file_info.category),
            'usage': self._score_usage(file_info.accessed),
            'location': self._score_location(file_info.path)
        }
        
        # Score pondéré
        final = (
            scores['size'] * self.WEIGHT_SIZE +
            scores['age'] * self.WEIGHT_AGE +
            scores['type'] * self.WEIGHT_TYPE +
            scores['usage'] * self.WEIGHT_USAGE +
            scores['location'] * self.WEIGHT_LOCATION
        )
        
        # Pénalité si c'est un doublon (plus supprimable)
        if file_info.is_duplicate:
            final = max(0, final - 30)
        
        return min(100, max(0, final))
    
    def _score_size(self, size_mb: float) -> float:
        """Plus le fichier est gros, plus il est intéressant à supprimer (score bas)"""
        # Normalisation : 0 Mo -> 0, 10 Go -> 100
        raw = min(100, (size_mb / self.MAX_SIZE_MB) * 100)
        return 100 - raw  # Inversé : gros = bas score
    
    def _score_age(self, modified: datetime) -> float:
        """Plus le fichier est vieux, plus il est supprimable (score bas)"""
        age_days = (datetime.now() - modified).days
        raw = min(100, (age_days / self.MAX_AGE_DAYS) * 100)
        return 100 - raw
    
    def _score_type(self, category: FileCategory) -> float:
        """Score selon le type de fichier"""
        type_scores = {
            FileCategory.CACHE: 10,       # très supprimable
            FileCategory.DUPLICATE: 15,
            FileCategory.INSTALLER: 25,
            FileCategory.MEDIA: 50,
            FileCategory.ARCHIVE: 55,
            FileCategory.DOCUMENT: 65,
            FileCategory.OTHER: 70,
            FileCategory.SYSTEM: 95,      # très important
        }
        return type_scores.get(category, 50)
    
    def _score_usage(self, accessed: datetime) -> float:
        """Fichier non utilisé récemment = plus supprimable"""
        days = (datetime.now() - accessed).days
        if days > 180:
            return 20
        if days > 90:
            return 40
        if days > 30:
            return 60
        return 80
    
    def _score_location(self, path: str) -> float:
        """Emplacement critique = plus important"""
        path_lower = path.lower()
        critical_patterns = [
            'windows', 'system32', 'program files',
            'appdata/roaming/microsoft',
            'boot', 'sys'
        ]
        for pattern in critical_patterns:
            if pattern in path_lower:
                return 90
        
        # Bureau / Documents = important
        if 'desktop' in path_lower or 'bureau' in path_lower:
            return 75
        if 'documents' in path_lower:
            return 65
        if 'downloads' in path_lower or 'téléchargements' in path_lower:
            return 40
        
        return 50
    
    def get_importance(self, score: float) -> Importance:
        """Convertit le score en niveau d'importance"""
        if score >= 85:
            return Importance.CRITICAL
        if score >= 60:
            return Importance.HIGH
        if score >= 25:
            return Importance.MEDIUM
        if score > 0:
            return Importance.LOW
        return Importance.SAFE
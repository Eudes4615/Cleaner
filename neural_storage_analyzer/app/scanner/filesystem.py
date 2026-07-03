import os
import time
from pathlib import Path
from datetime import datetime
from typing import List, Callable, Optional
from ..core.models import FileInfo, FileCategory
from ..core.scoring import ScoringEngine
from ..security.protection import SecurityManager

class FileSystemScanner:
    """Scanner robuste pour très gros volumes (500k+ fichiers)"""

    def __init__(self):
        self.scoring_engine = ScoringEngine()
        self.security = SecurityManager()
        self.total_files = 0
        self.processed_files = 0
        self._stop = False
        self.results = []

    def stop(self):
        """Arrête le scan proprement"""
        self._stop = True

    def scan(self, paths: List[str],
             progress_callback: Optional[Callable[[int, int], None]] = None,
             file_callback: Optional[Callable[[FileInfo], None]] = None,
             limit: int = 0) -> List[FileInfo]:
        """
        Scan avec limite optionnelle pour éviter la saturation mémoire.
        - limit = 0 : scan complet
        - limit = 10000 : ne garde que 10000 fichiers en mémoire
        """
        self.results = []
        self.total_files = 0
        self.processed_files = 0
        self._stop = False

        # 1. Compter les fichiers (avec limite pour ne pas bloquer)
        print("📊 Comptage des fichiers...")
        for path in paths:
            if not os.path.exists(path):
                continue
            try:
                for root, dirs, files in os.walk(path):
                    # Ignorer les dossiers système
                    dirs[:] = [d for d in dirs if not self._is_ignored_dir(d)]
                    self.total_files += len(files)
                    if self.total_files > 1000000:
                        break
            except PermissionError:
                continue

        if self.total_files == 0:
            print("⚠️ Aucun fichier trouvé.")
            return []

        print(f"📊 {self.total_files} fichiers à analyser")

        # 2. Scan proprement dit
        for path in paths:
            if not os.path.exists(path) or self._stop:
                continue
            self._scan_directory(path, progress_callback, file_callback, limit)
            if self._stop:
                break

        # 3. Tri par taille (les plus gros en premier)
        self.results.sort(key=lambda x: x.size_mb, reverse=True)
        return self.results

    def _scan_directory(self, directory: str,
                        progress_callback: Optional[Callable],
                        file_callback: Optional[Callable],
                        limit: int):
        """Scanne un dossier avec gestion des erreurs"""
        try:
            for root, dirs, files in os.walk(directory):
                if self._stop:
                    break

                # Ignorer les dossiers inutiles
                dirs[:] = [d for d in dirs if not self._is_ignored_dir(d)]

                for name in files:
                    if self._stop:
                        break

                    path = os.path.join(root, name)

                    # Limite mémoire
                    if limit > 0 and len(self.results) >= limit:
                        print(f"⚠️ Limite de {limit} fichiers atteinte, arrêt.")
                        self._stop = True
                        break

                    try:
                        stat = os.stat(path)
                        size_mb = stat.st_size / (1024 * 1024)

                        # Ignorer les fichiers vides ou trop petits (< 10 Ko)
                        if size_mb < 0.01:
                            self.processed_files += 1
                            continue

                        file_info = FileInfo(
                            path=path,
                            size_mb=size_mb,
                            created=datetime.fromtimestamp(stat.st_ctime),
                            modified=datetime.fromtimestamp(stat.st_mtime),
                            accessed=datetime.fromtimestamp(stat.st_atime),
                            extension=Path(path).suffix.lower(),
                            category=self._classify_file(path, size_mb),
                            score=0.0,
                            importance=None,
                            is_duplicate=False,
                            duplicate_of=None,
                            hash_sha256=None
                        )

                        # Calcul du score IA
                        file_info.score = self.scoring_engine.calculate_score(file_info)
                        file_info.importance = self.scoring_engine.get_importance(file_info.score)

                        # Sécurité : ne pas toucher aux fichiers système
                        if self.security.is_safe(path):
                            self.results.append(file_info)
                            if file_callback:
                                try:
                                    file_callback(file_info)
                                except Exception as e:
                                    print(f"⚠️ Erreur callback : {e}")

                        self.processed_files += 1

                        # Progression
                        if progress_callback and self.total_files > 0:
                            try:
                                progress_callback(self.processed_files, self.total_files)
                            except Exception:
                                pass

                        # Pause pour éviter de saturer le CPU
                        if self.processed_files % 1000 == 0:
                            time.sleep(0.001)

                    except (PermissionError, OSError, FileNotFoundError):
                        self.processed_files += 1
                        continue

        except PermissionError:
            pass
        except Exception as e:
            print(f"⚠️ Erreur dans {directory} : {e}")

    def _is_ignored_dir(self, name: str) -> bool:
        """Dossiers à ignorer pour gagner du temps"""
        ignored = {
            '.git', '.svn', '.hg', '.bzr',
            'node_modules', 'vendor', 'bower_components',
            '__pycache__', '.pytest_cache', '.mypy_cache',
            'venv', '.venv', 'env', '.env',
            'build', 'dist', 'target', 'out',
            '.idea', '.vscode', '.vs',
            'Recycler', '$Recycle.Bin', 'System Volume Information',
            'Temp', 'tmp', 'Cache', 'caches'
        }
        name_lower = name.lower()
        return name_lower in ignored or name_lower.startswith('.') or name_lower.startswith('$')

    def _classify_file(self, path: str, size_mb: float) -> FileCategory:
        ext = Path(path).suffix.lower()
        pl = path.lower()

        # Caches
        if ext in {'.tmp', '.temp', '.cache', '.log', '.bak', '.old', '.dump', '.crash'}:
            return FileCategory.CACHE
        if 'temp' in pl or 'cache' in pl or 'tmp' in pl:
            return FileCategory.CACHE

        # Installateurs
        if ext in {'.exe', '.msi', '.apk', '.dmg', '.deb', '.rpm'}:
            return FileCategory.INSTALLER

        # Médias
        if ext in {'.mp4', '.mkv', '.avi', '.mov', '.mp3', '.wav', '.flac', '.aac'}:
            return FileCategory.MEDIA
        if ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico'}:
            return FileCategory.MEDIA

        # Archives
        if ext in {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.iso'}:
            return FileCategory.ARCHIVE

        # Documents
        if ext in {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.rtf', '.odt', '.ods'}:
            return FileCategory.DOCUMENT

        # Système
        if ext in {'.dll', '.sys', '.ini', '.cfg', '.conf'} and ('windows' in pl or 'system32' in pl):
            return FileCategory.SYSTEM

        return FileCategory.OTHER
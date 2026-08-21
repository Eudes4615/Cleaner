# Neural Storage Analyzer

**Neural Storage Analyzer** est une application desktop PyQt6 qui analyse un ou plusieurs dossiers, classe les fichiers selon des règles heuristiques, calcule un score d’attention et recherche les doublons par fingerprint puis par hash. Les résultats sont conservés dans une base SQLite locale.

> Le projet n’efface pas automatiquement les fichiers. Les opérations de nettoyage et de restauration restent désactivées tant qu’une politique de suppression, de corbeille et de rollback complète n’est pas implémentée.

## Fonctionnalités disponibles

| Fonctionnalité | État |
|---|---|
| Sélection d’un dossier depuis l’interface | Disponible |
| Scan avec filtres de taille et de répertoires système | Disponible |
| Classification cache, média, installateur, archive, document, système | Disponible |
| Score d’ancienneté et de taille | Disponible |
| Persistance SQLite des scans et fichiers | Disponible |
| Détection de doublons | Disponible, à valider sur un jeu de données réel |
| Cache de scan incrémental | Disponible au niveau du module dédié |
| Suppression automatique | Désactivée |
| Restauration automatique | Désactivée |
| Paramètres graphiques | Désactivés dans cette version |

## Installation

Le projet nécessite Python 3.10 ou une version ultérieure. Il est recommandé d’utiliser un environnement virtuel :

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\\Scripts\\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Lancement

Depuis la racine du dépôt :

```bash
python -m app.main
```

Une fois l’application ouverte, cliquez sur **Choisir un dossier**, sélectionnez un répertoire, puis lancez le scan. Le chemin n’est plus codé en dur : l’interface accepte les chemins disponibles sur Windows, Linux et macOS.

La base SQLite principale est créée dans :

```text
~/.neural_storage_analyzer.db
```

Le cache incrémental utilise une base distincte :

```text
~/.neural_storage_cache.db
```

## Architecture

```text
app/main.py
    └── app/ui/main_window.py
            └── app/services/scan_service.py
                    ├── app/engine/scanner.py
                    ├── app/engine/classifier.py
                    ├── app/engine/hasher.py
                    ├── app/repository/scan_repo.py
                    └── app/repository/file_repo.py
                            └── app/core/database.py
```

Le scan est orchestré par `ScanService`. Le moteur énumère les fichiers, le classificateur produit une catégorie et un score, le hacheur calcule un fingerprint ou un hash selon la taille, puis les repositories enregistrent les données par lots dans SQLite. Le service de doublons effectue ensuite la seconde passe sur les fichiers candidats.

Le module `app/scanner/incremental.py` s’appuie sur `app/storage/cache.py` pour ne rescanner que les fichiers nouveaux ou modifiés. Le cache sait maintenant lire la date du dernier scan et reconstruire un objet `FileInfo` à partir de son entrée SQLite.

## Validation locale

Une vérification syntaxique des modules principaux peut être exécutée ainsi :

```bash
python -m py_compile \
  app/core/database.py \
  app/repository/file_repo.py \
  app/services/scan_service.py \
  app/engine/scanner.py \
  app/storage/cache.py \
  app/scanner/incremental.py \
  app/ui/main_window.py
```

Pour les tests fonctionnels, utilisez de préférence un dossier temporaire contenant uniquement des fichiers de test. L’application peut parcourir un grand nombre de fichiers et le hachage des fichiers volumineux peut être coûteux.

## Limites connues

La suppression et la restauration sont volontairement désactivées dans l’interface : le repository des actions journalise des opérations, mais ne réalise pas encore un rollback complet avec la corbeille système. Le scan principal reste synchrone dans le service PyQt6 ; une prochaine amélioration pourra déplacer le travail dans un worker `QThread` afin d’éviter tout blocage de l’interface sur un disque volumineux.

Les règles de classification et de scoring sont heuristiques. Elles ne constituent pas une preuve qu’un fichier peut être supprimé. Toute décision de nettoyage doit être confirmée par l’utilisateur et, pour les fichiers système ou professionnels, par une vérification adaptée au contexte.

## Développement

Les changements de schéma SQLite sont conçus pour être additifs. Le champ `status` des scans est ajouté automatiquement aux bases existantes qui ne le possèdent pas encore. Les transactions du backend sont regroupées et annulées en cas d’exception.

Avant une contribution, vérifiez la syntaxe Python, utilisez un dossier de test isolé et ne commitez pas les bases SQLite, les journaux, les rapports générés ni les répertoires `__pycache__`.

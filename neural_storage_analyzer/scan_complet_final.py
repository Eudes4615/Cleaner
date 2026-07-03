import os
import csv
import time
from pathlib import Path
from datetime import datetime

print("🧠 SCAN COMPLET DU DISQUE (fichiers > 50 Mo)")
print("="*70)

# ============================================================
# 1. Dossiers à IGNORER (sécurité + perf)
# ============================================================

EXCLUDED_DIRS = {
    'Windows', 'Program Files', 'Program Files (x86)', 'System32', 'System',
    'Boot', 'Temp', 'tmp', 'Cache', 'caches', 'Logs',
    'System Volume Information', '$Recycle.Bin', 'Recovery', 'Config.Msi',
    'node_modules', '__pycache__', '.git', 'venv', '.venv',
    'build', 'dist', 'target', 'out',
}

def is_excluded_dir(name):
    name_lower = name.lower()
    return name in EXCLUDED_DIRS or name.startswith('.') or name.startswith('$')

# ============================================================
# 2. Détection des lecteurs
# ============================================================

def get_drives():
    drives = []
    for letter in 'CDEFGHIJKLMNOPQRSTUVWXYZ':
        path = letter + ':/'
        if os.path.exists(path):
            drives.append(path)
    return drives

drives = get_drives()
print(f"📂 Lecteurs détectés : {drives}")

# ============================================================
# 3. Scan principal
# ============================================================

MIN_SIZE_MB = 50  # Ne garder que les fichiers > 50 Mo
results = []
total_files_checked = 0
start_time = time.time()

for drive in drives:
    print(f"\n🔍 Scan de {drive}...")
    if not os.path.exists(drive):
        continue

    try:
        for root, dirs, files in os.walk(drive):
            dirs[:] = [d for d in dirs if not is_excluded_dir(d)]

            for name in files:
                total_files_checked += 1
                if total_files_checked % 1000 == 0:
                    elapsed = time.time() - start_time
                    speed = total_files_checked / elapsed if elapsed > 0 else 0
                    print(f"   {total_files_checked} fichiers analysés ({speed:.0f}/s)")

                file_path = os.path.join(root, name)
                try:
                    stat = os.stat(file_path)
                    size_mb = stat.st_size / (1024 * 1024)

                    if size_mb > MIN_SIZE_MB:
                        results.append({
                            'path': file_path,
                            'size_mb': round(size_mb, 2),
                            'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                            'drive': drive
                        })
                except (PermissionError, OSError, FileNotFoundError):
                    continue

    except PermissionError:
        print(f"   ⚠️ Accès refusé à {drive}, certains dossiers ignorés.")
        continue

# ============================================================
# 4. Résultats
# ============================================================

print("\n📊 Tri par taille...")
results.sort(key=lambda x: x['size_mb'], reverse=True)

total_size = sum(f['size_mb'] for f in results)

print("\n" + "="*70)
print("📊 RÉSULTATS DU SCAN COMPLET")
print("="*70)
print(f"✅ Fichiers analysés : {total_files_checked}")
print(f"📦 Fichiers > {MIN_SIZE_MB} Mo : {len(results)}")
print(f"💾 Espace total : {total_size:.2f} Mo ({total_size/1024:.2f} Go)")

if results:
    print("\n📄 TOP 30 DES PLUS GROS FICHIERS :")
    print("-"*70)
    for i, f in enumerate(results[:30], 1):
        size_str = f"{f['size_mb']:.2f} Mo" if f['size_mb'] < 1024 else f"{f['size_mb']/1024:.2f} Go"
        print(f"{i:2d}. {Path(f['path']).name} ({size_str})")
        print(f"     {f['path']}\n")

# ============================================================
# 5. Rapport CSV
# ============================================================

report_file = 'rapport_full_disk.csv'
with open(report_file, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(['Chemin', 'Taille (Mo)', 'Modifié', 'Disque'])
    for f in results:
        writer.writerow([f['path'], f['size_mb'], f['modified'], f['drive']])

print(f"\n💾 Rapport complet : {report_file}")

elapsed = time.time() - start_time
print(f"⏱️ Temps total : {elapsed:.1f} secondes ({elapsed/60:.1f} minutes)")
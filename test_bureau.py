import os
from pathlib import Path
from datetime import datetime

print("🧪 TEST SCAN SIMPLE - DOSSIER BUREAU")
print("="*60)

# Test sur le Bureau
desktop = Path.home() / 'Desktop'
if not desktop.exists():
    desktop = Path.home() / 'Bureau'

print(f"📂 Scan de : {desktop}")

results = []
total = 0

for root, dirs, files in os.walk(desktop):
    # Ignorer les dossiers cachés
    dirs[:] = [d for d in dirs if not d.startswith('.')]
    for name in files:
        file_path = os.path.join(root, name)
        try:
            stat = os.stat(file_path)
            size_mb = stat.st_size / (1024 * 1024)
            total += 1

            # Garder TOUS les fichiers (sauf ceux < 10 Ko)
            if size_mb >= 0.01:
                results.append({
                    'path': file_path,
                    'size_mb': round(size_mb, 2),
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d')
                })

            if total % 100 == 0:
                print(f"   {total} fichiers trouvés...")

        except (PermissionError, OSError):
            continue

# Tri par taille
results.sort(key=lambda x: x['size_mb'], reverse=True)

print("\n" + "="*60)
print(f"✅ {total} fichiers trouvés")
print(f"📦 {len(results)} fichiers > 10 Ko")

# Afficher les 10 plus gros
print("\n📄 TOP 10 DES PLUS GROS FICHIERS :")
for i, r in enumerate(results[:10], 1):
    print(f"{i:2d}. {Path(r['path']).name} ({r['size_mb']:.2f} Mo)")

# Sauvegarde
with open('test_rapport.txt', 'w', encoding='utf-8') as f:
    for r in results:
        f.write(f"{r['path']} | {r['size_mb']} Mo | {r['modified']}\n")

print(f"\n📄 Rapport complet dans : test_rapport.txt")
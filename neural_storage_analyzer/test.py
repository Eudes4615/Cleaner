from app.scanner.filesystem import FileSystemScanner
from pathlib import Path

print("🧪 Test du scanner sur un petit dossier")
scanner = FileSystemScanner()

# Test sur le dossier Téléchargements uniquement
test_path = str(Path.home() / 'Downloads')
if not Path(test_path).exists():
    test_path = str(Path.home() / 'Téléchargements')

print(f"📂 Scan de : {test_path}")

def progress(p, t):
    if p % 100 == 0:  # Affiche tous les 100 fichiers
        print(f"   {p}/{t} fichiers analysés...")

results = scanner.scan([test_path], progress)

print(f"✅ {len(results)} fichiers trouvés")
if results:
    print("📄 Top 5 des plus gros :")
    for f in sorted(results, key=lambda x: x.size_mb, reverse=True)[:5]:
        print(f"   {f.path} ({f.size_mb:.2f} Mo)")
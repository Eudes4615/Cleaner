from .database import Database

class SchemaManager:
    CURRENT_VERSION = 1

    @classmethod
    def ensure_schema(cls):
        db = Database()
        # Vérifier si la table schema_info existe
        db.execute("""
            CREATE TABLE IF NOT EXISTS schema_info (
                version INTEGER PRIMARY KEY
            )
        """)
        row = db.fetchone("SELECT version FROM schema_info")
        if not row:
            db.execute(f"INSERT INTO schema_info (version) VALUES ({cls.CURRENT_VERSION})")
        elif row[0] < cls.CURRENT_VERSION:
            cls._migrate(row[0])

    @classmethod
    def _migrate(cls, old_version: int):
        # Logique de migration future
        print(f"⚠️ Migration de la base de {old_version} à {cls.CURRENT_VERSION}")
        db = Database()
        db.execute(f"UPDATE schema_info SET version = {cls.CURRENT_VERSION}")
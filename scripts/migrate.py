#!/usr/bin/env python3
"""
Skrypt do zarządzania migracjami bazy danych z Alembic
"""
import asyncio
import sys
import os
from pathlib import Path

# Dodaj src do ścieżki Python
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.db.main import init_db
from src.config import config


async def create_tables():
    """Tworzy tabele w bazie danych (tylko dla development)"""
    print("🔧 Creating database tables...")
    await init_db()
    print("✅ Database tables created successfully!")


async def migrate():
    """Uruchamia migracje Alembic"""
    import subprocess
    
    print("🔄 Running Alembic migrations...")
    
    # Ustaw zmienną środowiskową dla Alembic
    os.environ["DATABASE_URL"] = config.DATABASE_URL
    
    try:
        # Uruchom migracje
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Migrations completed successfully!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)


async def create_migration(message: str):
    """Tworzy nową migrację"""
    import subprocess
    
    print(f"📝 Creating migration: {message}")
    
    try:
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", message],
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Migration created successfully!")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration creation failed: {e}")
        print(f"Error output: {e.stderr}")
        sys.exit(1)


async def show_migrations():
    """Pokazuje status migracji"""
    import subprocess
    
    print("📊 Migration status:")
    
    try:
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        
        result = subprocess.run(
            ["alembic", "history", "--verbose"],
            capture_output=True,
            text=True,
            check=True
        )
        print("\nMigration history:")
        print(result.stdout)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to show migrations: {e}")
        print(f"Error output: {e.stderr}")


def main():
    """Główna funkcja"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/migrate.py <command>")
        print("Commands:")
        print("  create-tables  - Create database tables (development only)")
        print("  migrate        - Run migrations")
        print("  create <msg>   - Create new migration")
        print("  status         - Show migration status")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create-tables":
        asyncio.run(create_tables())
    elif command == "migrate":
        asyncio.run(migrate())
    elif command == "create":
        if len(sys.argv) < 3:
            print("❌ Please provide migration message")
            sys.exit(1)
        message = sys.argv[2]
        asyncio.run(create_migration(message))
    elif command == "status":
        asyncio.run(show_migrations())
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()


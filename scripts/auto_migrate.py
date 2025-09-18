#!/usr/bin/env python3
"""
Automatyczne uruchamianie migracji przy starcie aplikacji
"""
import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Dodaj src do ścieżki Python
project_root = Path(__file__).parent.parent

sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from src.config import config

async def auto_migrate():
    """Automatycznie uruchamia migracje przy starcie"""
    print("🔄 Auto-migrating database...")
    
    # Ustaw zmienne środowiskowe
    env = os.environ.copy()
    env["DATABASE_URL"] = config.DATABASE_URL
    
    try:
        # Sprawdź status migracji
        result = subprocess.run(
            ["python", "-m", "alembic", "current"],
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        print(f"📊 Current migration status: {result.stdout.strip()}")
        
        # Uruchom migracje
        result = subprocess.run(
            ["python", "-m", "alembic", "upgrade", "head"],
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        
        print("✅ Database migrations completed successfully!")
        if result.stdout:
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        return False


if __name__ == "__main__":
    success = asyncio.run(auto_migrate())
    if not success:
        sys.exit(1)

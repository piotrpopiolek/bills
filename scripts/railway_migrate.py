#!/usr/bin/env python3
"""
Skrypt do uruchamiania migracji Alembic w Railway
"""
import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Dodaj src do ścieżki Python
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config import config


def run_alembic_command(command: list):
    """Uruchamia komendę Alembic"""
    print(f"🔄 Running: alembic {' '.join(command)}")
    
    # Ustaw zmienne środowiskowe
    env = os.environ.copy()
    env["DATABASE_URL"] = config.DATABASE_URL
    
    try:
        result = subprocess.run(
            ["python", "-m", "alembic"] + command,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Command completed successfully!")
        if result.stdout:
            print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        return False


def main():
    """Główna funkcja"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/railway_migrate.py <alembic_command>")
        print("Examples:")
        print("  python scripts/railway_migrate.py current")
        print("  python scripts/railway_migrate.py upgrade head")
        print("  python scripts/railway_migrate.py history")
        print("  python scripts/railway_migrate.py revision --autogenerate -m 'Add new field'")
        sys.exit(1)
    
    command = sys.argv[1:]
    success = run_alembic_command(command)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

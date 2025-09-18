#!/usr/bin/env python3
"""
Skrypt do testowania migracji lokalnie
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


async def test_migrations():
    """Testuje migracje lokalnie"""
    print("🧪 Testing migrations locally...")
    
    # Ustaw zmienne środowiskowe
    env = os.environ.copy()
    env["DATABASE_URL"] = config.DATABASE_URL
    
    commands = [
        ["current"],
        ["history", "--verbose"],
        ["upgrade", "head"],
        ["current"],
    ]
    
    for command in commands:
        print(f"\n🔄 Running: alembic {' '.join(command)}")
        
        try:
            result = subprocess.run(
                ["python", "-m", "alembic"] + command,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            
            print("✅ Success!")
            if result.stdout:
                print(result.stdout)
                
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed: {e}")
            if e.stderr:
                print(f"Error: {e.stderr}")
            if e.stdout:
                print(f"Output: {e.stdout}")
            return False
    
    print("\n✅ All migration tests passed!")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_migrations())
    if not success:
        sys.exit(1)

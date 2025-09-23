#!/usr/bin/env python3
"""
Wrapper dla Alembic w Railway
Rozwiązuje problem z brakiem dostępu do alembic.__main__
"""
import sys
import os
import subprocess
from pathlib import Path

# Dodaj src do ścieżki Python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main():
    """Uruchom alembic przez subprocess"""
    try:
        # Ustaw zmienne środowiskowe
        env = os.environ.copy()
        
        # Spróbuj uruchomić alembic przez python -m
        cmd = [sys.executable, "-m", "alembic"] + sys.argv[1:]
        
        print("Alembic Wrapper")
        print(f"Project root: {project_root}")
        print(f"Command: {' '.join(cmd)}")
        
        # Uruchom alembic
        result = subprocess.run(cmd, env=env)
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"Error running alembic: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
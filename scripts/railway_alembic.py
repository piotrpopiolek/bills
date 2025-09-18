#!/usr/bin/env python3
"""
Prosty skrypt do uruchamiania migracji Alembic w Railway
Bez zależności od zewnętrznych modułów
"""
import os
import sys
import subprocess


def run_alembic_command(command: list):
    """Uruchamia komendę Alembic"""
    print(f"🔄 Running: alembic {' '.join(command)}")
    
    # Ustaw zmienne środowiskowe
    env = os.environ.copy()
    
    # Sprawdź czy DATABASE_URL jest ustawione
    database_url = env.get("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set!")
        print("Available environment variables:")
        for key, value in env.items():
            if "DATABASE" in key.upper() or "DB" in key.upper():
                print(f"  {key}={value}")
        return False
    
    print(f"📊 Using DATABASE_URL: {database_url[:50]}...")
    
    # Spróbuj najpierw bezpośrednio uruchomić alembic
    try:
        result = subprocess.run(
            ["alembic"] + command,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print("✅ Command completed successfully!")
        if result.stdout:
            print(result.stdout)
        return True
    except FileNotFoundError:
        print("❌ Alembic not found in PATH!")
        print("Trying python -m alembic...")
    except subprocess.CalledProcessError as e:
        print(f"❌ Alembic command failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        print("Trying python -m alembic...")
    
    # Fallback: spróbuj python -m alembic
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
        print(f"❌ Python -m alembic failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        return False
    except FileNotFoundError:
        print("❌ Python not found!")
        return False


def main():
    """Główna funkcja"""
    if len(sys.argv) < 2:
        print("Usage: python scripts/railway_alembic.py <alembic_command>")
        print("Examples:")
        print("  python scripts/railway_alembic.py current")
        print("  python scripts/railway_alembic.py upgrade head")
        print("  python scripts/railway_alembic.py history")
        print("  python scripts/railway_alembic.py revision --autogenerate -m 'Add new field'")
        print("\nEnvironment check:")
        print(f"  DATABASE_URL: {'Set' if os.environ.get('DATABASE_URL') else 'Not set'}")
        print(f"  PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")
        sys.exit(1)
    
    command = sys.argv[1:]
    success = run_alembic_command(command)
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()

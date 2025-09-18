#!/usr/bin/env python3
"""
Skrypt do debugowania środowiska Railway
"""
import os
import sys
import subprocess
from pathlib import Path


def debug_environment():
    """Debuguje środowisko Railway"""
    print("🔍 Railway Environment Debug")
    print("=" * 50)
    
    # Python info
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path[:3]}...")
    
    # Working directory
    print(f"Working directory: {os.getcwd()}")
    print(f"Script location: {Path(__file__).parent}")
    
    # Environment variables
    print("\n📊 Environment Variables:")
    important_vars = [
        "DATABASE_URL", "PORT", "ENVIRONMENT", "PYTHONPATH",
        "PATH", "PYTHON_VERSION", "RAILWAY_ENVIRONMENT"
    ]
    
    for var in important_vars:
        value = os.environ.get(var)
        if value:
            if "DATABASE_URL" in var:
                print(f"  {var}: {value[:50]}...")
            else:
                print(f"  {var}: {value}")
        else:
            print(f"  {var}: Not set")
    
    # Check if alembic is available
    print("\n🔧 Alembic Check:")
    try:
        result = subprocess.run(
            ["python", "-c", "import alembic; print('Alembic version:', alembic.__version__)"],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"  ✅ {result.stdout.strip()}")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Alembic not available: {e.stderr}")
    
    # Check if alembic command works
    print("\n🚀 Alembic Command Check:")
    try:
        result = subprocess.run(
            ["python", "-m", "alembic", "--help"],
            capture_output=True,
            text=True,
            check=True
        )
        print("  ✅ python -m alembic works")
    except subprocess.CalledProcessError as e:
        print(f"  ❌ python -m alembic failed: {e.stderr}")
    
    # Check files
    print("\n📁 File Check:")
    files_to_check = [
        "alembic.ini",
        "alembic/env.py",
        "alembic/versions",
        "requirements.txt"
    ]
    
    for file_path in files_to_check:
        path = Path(file_path)
        if path.exists():
            print(f"  ✅ {file_path} exists")
        else:
            print(f"  ❌ {file_path} missing")


if __name__ == "__main__":
    debug_environment()

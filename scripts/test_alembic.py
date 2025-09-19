#!/usr/bin/env python3
"""
Test skryptu alembic w Railway
"""
import sys
import os
from pathlib import Path

# Dodaj src do ścieżki Python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("🔍 Testing Alembic in Railway...")
print(f"📁 Project root: {project_root}")
print(f"🐍 Python version: {sys.version}")
print(f"📦 Python path: {sys.path[:3]}...")

# Test importu alembic
try:
    import alembic
    print(f"✅ Alembic imported successfully: {alembic.__version__}")
except ImportError as e:
    print(f"❌ Failed to import alembic: {e}")
    sys.exit(1)

# Test konfiguracji alembic
try:
    from alembic.config import Config
    from alembic import command
    
    # Sprawdź czy alembic.ini istnieje
    alembic_ini = project_root / "alembic.ini"
    if alembic_ini.exists():
        print(f"✅ alembic.ini found: {alembic_ini}")
        
        # Utwórz konfigurację
        config = Config(str(alembic_ini))
        print(f"✅ Alembic config loaded")
        
        # Test komendy current
        print("🔄 Testing alembic current...")
        command.current(config)
        print("✅ alembic current works!")
        
    else:
        print(f"❌ alembic.ini not found: {alembic_ini}")
        
except Exception as e:
    print(f"❌ Error testing alembic: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ All tests passed!")

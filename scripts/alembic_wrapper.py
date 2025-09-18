#!/usr/bin/env python3
"""
Wrapper dla Alembic w Railway
Rozwiązuje problem z brakiem dostępu do alembic.__main__
"""
import sys
import os
from pathlib import Path

# Dodaj src do ścieżki Python
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# Import alembic i uruchom główną funkcję
try:
    from alembic.config import main as alembic_main
    from alembic import __version__
    
    print(f"🚀 Alembic Wrapper v{__version__}")
    print(f"📁 Project root: {project_root}")
    print(f"🔧 Command: {' '.join(sys.argv[1:])}")
    
    # Uruchom alembic z argumentami
    alembic_main()
    
except ImportError as e:
    print(f"❌ Failed to import alembic: {e}")
    print("Available modules:")
    import pkgutil
    for importer, modname, ispkg in pkgutil.iter_modules():
        if 'alembic' in modname.lower():
            print(f"  - {modname}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error running alembic: {e}")
    sys.exit(1)

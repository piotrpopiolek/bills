# FastAPI Bills App

## Jak uruchomić

1. Zainstaluj zależności:

   ```bash
   pip install -r requirements.txt
   ```

2. Skonfiguruj bazę danych:

   ```bash
   # Uruchom migracje
   python scripts/migrate.py migrate
   ```

3. Uruchom serwer developerski:
   ```bash
   uvicorn main:app --reload
   ```

Aplikacja będzie dostępna pod adresem http://127.0.0.1:8000

## Zarządzanie migracjami

### Uruchomienie migracji

```bash
python scripts/migrate.py migrate
```

### Tworzenie nowej migracji

```bash
python scripts/migrate.py create "Add new field to table"
```

### Sprawdzenie statusu migracji

```bash
python scripts/migrate.py status
```

### Bezpośrednie użycie Alembic

```bash
# Uruchom migracje
alembic upgrade head

# Utwórz migrację
alembic revision --autogenerate -m "Description"

# Sprawdź status
alembic current
alembic history
```

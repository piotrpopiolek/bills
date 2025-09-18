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

## Railway Deployment

### Uruchomienie migracji w Railway

```bash
# Skonfiguruj Alembic w Railway
railway run python scripts/railway_setup.py

# Sprawdź status migracji
railway run python scripts/railway_alembic.py current

# Uruchom migracje
railway run python scripts/railway_alembic.py upgrade head

# Sprawdź historię migracji
railway run python scripts/railway_alembic.py history

# Ręczne uruchamianie (jeśli inne nie działają)
railway run python scripts/railway_manual.py current
railway run python scripts/railway_manual.py upgrade head
```

### Automatyczne migracje

Aplikacja automatycznie uruchamia migracje przy starcie. Jeśli chcesz wyłączyć to zachowanie, usuń kod z `main.py` w funkcji `lifespan`.

### Testowanie migracji lokalnie

```bash
python scripts/test_migrations.py
```

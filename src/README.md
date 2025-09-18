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
# Testuj alembic w Railway
railway run python scripts/test_alembic.py

# Uruchom migracje
railway run migrate

# Cofnij ostatnią migrację
railway run migrate-rollback

# Rollback i ponowne wprowadzenie migracji
railway run migrate-rollback-remigrate

# Sprawdź status migracji
railway run migrate-status

# Sprawdź historię migracji
railway run migrate-history
```

### Bezpośrednie komendy alembic

```bash
# Uruchom migracje przez wrapper
railway run python scripts/alembic_wrapper.py upgrade head

# Cofnij migrację przez wrapper
railway run python scripts/alembic_wrapper.py downgrade -1

# Sprawdź status przez wrapper
railway run python scripts/alembic_wrapper.py current

# Sprawdź historię przez wrapper
railway run python scripts/alembic_wrapper.py history --verbose

# Utwórz nową migrację przez wrapper
railway run python scripts/alembic_wrapper.py revision --autogenerate -m "Add new field"
```

### Automatyczne migracje

Aplikacja automatycznie uruchamia migracje przy starcie. Jeśli chcesz wyłączyć to zachowanie, usuń kod z `main.py` w funkcji `lifespan`.

### Testowanie migracji lokalnie

```bash
python scripts/test_migrations.py
```

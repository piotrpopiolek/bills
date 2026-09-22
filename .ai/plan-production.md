Faza 0: Przygotowanie Struktury Monorepo
Zanim dotkniesz serwerów, musisz uporządkować repozytorium, aby CI/CD "rozumiało", co gdzie leży.

[ ] Standaryzacja struktury katalogów: Upewnij się, że repozytorium wygląda tak:

Plaintext

/ (root)
├── .github/workflows/ # Tutaj trafią pliki YAML dla Actions
├── backend/ # Cały kod FastAPI + Dockerfile backendu
├── astro/ # Cały kod Astro/React + Dockerfile frontendu + nginx.conf
└── README.md
[ ] Pliki .dockerignore: Stwórz osobny .dockerignore w folderze backend/ i astro/, aby nie kopiować do kontenerów śmieci (np. node_modules, .venv, .git, **pycache**).

Faza 1: Konteneryzacja (Docker)
Kontener ma być taki sam lokalnie i na produkcji.

1.1. Backend (FastAPI)
[ ] Stwórz backend/Dockerfile:

Baza: python:3.13-slim.

Ustaw WORKDIR /app.

Zainstaluj zależności (najlepiej rozdzielając COPY requirements.txt . od COPY . . dla cache'owania warstw).

Uruchomienie: CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"].

[ ] Telegram Webhook:

✅ **JUŻ ZAIMPLEMENTOWANE**: Projekt już używa webhooków (TelegramBotService.process_webhook_update). Webhook jest dostępny pod endpointem `/api/v1/webhooks/telegram`. W produkcji upewnij się, że:

- TELEGRAM_WEBHOOK_URL jest ustawione na publiczny URL backendu (np. https://api.example.com/api/webhooks/telegram)
- TELEGRAM_WEBHOOK_SECRET jest ustawione dla bezpieczeństwa
- Webhook jest zarejestrowany w Telegramie (można to zrobić przez API lub dashboard Telegram)

  1.2. Frontend (Astro + Nginx)
  To kluczowy punkt. Nginx będzie serwował pliki statyczne ORAZ działał jako bramka do API.

[ ] Stwórz astro/nginx.conf:

Skonfiguruj blok server, który:

Obsługuje pliki statyczne (root /usr/share/nginx/html).

Obsługuje routing SPA (try_files $uri $uri/ /index.html).

Proxy do backendu: Przekierowuje location /api/ do serwisu backendu w sieci wewnętrznej.

[ ] Stwórz astro/Dockerfile (Multi-stage):

Stage 1 (Build): Obraz node:20. Wykonaj npm install i npm run build.

Stage 2 (Run): Obraz nginx:alpine. Skopiuj folder dist/ ze Stage 1 do katalogu html Nginxa. Skopiuj też swój nginx.conf.

Faza 2: Baza Danych (Supabase)
[ ] Tryb Transakcyjny (Pooler):

W panelu Supabase przejdź do Database -> Connection Pooling.

Skopiuj Transaction Pooler URL (port 6543). Python w trybie async na serverlessie potrafi szybko wyczerpać limity bezpośrednich połączeń.

[ ] Migracje (Supabase):

Migracje znajdują się w `supabase/migrations/`.

Opcje wdrożenia migracji:

- **Opcja 1 (Rekomendowana)**: Użyj Supabase CLI w skrypcie prestart.sh:
  ```bash
  supabase db push --db-url $DATABASE_URL
  ```
- **Opcja 2**: Uruchamiaj migracje ręcznie przed wdrożeniem (mniej automatyczne)
- **Opcja 3**: Użyj Supabase Dashboard do aplikowania migracji

Przygotuj skrypt (np. w backend/prestart.sh), który uruchamia migracje przed startem aplikacji. Dzięki temu baza zaktualizuje się sama przy każdym wdrożeniu nowej wersji.

Faza 4: CI/CD (GitHub Actions)
Automatyzacja testów i wdrożeń z uwzględnieniem Monorepo.

4.1. Pipeline Backend (.github/workflows/backend.yml)
[ ] Trigger: Push do main/master, ale z filtrem paths: ['backend/**'].

[ ] Jobs:

test: Instalacja Pythona, pip install, pytest (mockowanie API OpenAI i Telegrama).

- Użyj working-directory: ./backend (podobnie jak w istniejącym workflow CI)

**Uwaga**: CI jest w `.github/workflows/ci.yml`. Deploy zostaw poza tym workflow, dopóki nie ma wybranego hostingu.

4.2. Pipeline Frontend (.github/workflows/frontend.yml)
[ ] Trigger: Push do main/master, filtr paths: ['astro/**'].

[ ] Jobs:

test: npm install, npm run test (Vitest), npm run build (sprawdzenie czy build w ogóle przechodzi).

- Użyj working-directory: ./astro (podobnie jak w istniejącym pull-request.yml)
- Sprawdź czy projekt ma skrypt `test` w package.json

e2e: Opcjonalnie Playwright dla kluczowych ścieżek (np. logowanie).

- Sprawdź czy istnieją już testy E2E w projekcie (szukaj w astro/e2e/)

**Uwaga**: Istnieje już `.github/workflows/pull-request.yml` z lintowaniem Astro. Rozważ rozszerzenie go o testy lub utworzenie osobnych workflow dla deploy.

Faza 5: "Day 2 Operations" (Monitoring i Utrzymanie)
Twoja aplikacja już działa. Teraz sprawiamy, żeby działała długo i stabilnie.

[ ] Sentry (Error Tracking):

Zainstaluj SDK Sentry w FastAPI oraz w React/Astro. To absolutna podstawa, żeby widzieć błędy 500 i crashe JS u użytkowników.

[ ] Healthchecki:

✅ **JUŻ ZAIMPLEMENTOWANE**: Endpoint `/health` już istnieje w `backend/src/health.py`. Dostępne są dwa endpointy:

- `/health` - podstawowy healthcheck
- `/health/db` - healthcheck z testem połączenia do bazy

Ustaw healthcheck hostingu na `/health`.

Podsumowanie Strategii
Monorepo: backend i frontend budują się osobnymi Dockerfile.

Architektura: Nginx (Frontend) jest twoją tarczą i routerem. Ukrywa Backend przed światem (za wyjątkiem webhooków).

Baza: Connection Pooler to "must-have" przy Pythonie i chmurze.

## ✅ Co już jest zaimplementowane:

- ✅ Healthcheck endpoint (`/health`)
- ✅ Telegram webhook (nie polling)
- ✅ Sentry SDK w requirements.txt (backend)
- ✅ Struktura monorepo (backend/, astro/)
- ✅ GitHub Actions workflow dla PR (lint)

## ⚠️ Co wymaga aktualizacji/korekty:

- ⚠️ Plan mówił o `/frontend` - poprawione na `/astro`
- ⚠️ Plan mówił o Alembic - projekt używa Supabase migrations
- ⚠️ Brak Dockerfile w backend/ i astro/
- ⚠️ Brak .dockerignore w backend/ i astro/
- ⚠️ Brak nginx.conf w astro/
- ⚠️ Brak workflow dla deploy (tylko PR workflow)
- ⚠️ Brak konfiguracji Sentry w frontendzie
- ⚠️ Brak prestart.sh dla migracji Supabase

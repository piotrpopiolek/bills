# 🚂 Railway Setup Guide

## 📋 Wymagane zmienne środowiskowe w Railway

### 🔐 Database

Railway automatycznie ustawia `DATABASE_URL` dla PostgreSQL. Upewnij się, że używa `postgresql+asyncpg://`:

```bash
# Railway automatycznie ustawia to
DATABASE_URL=postgresql+asyncpg://username:password@host:port/database
```

### 🔴 Redis

```bash
REDIS_HOST=your-redis-host
REDIS_PORT=6379
REDIS_PASSWORD=your-redis-password

# Alternatywne nazwy dla Railway:
REDIS_HOSTNAME=your-redis-host
REDIS_SERVICE_HOST=your-redis-host
REDIS_SERVICE_PORT=6379
REDIS_AUTH=your-redis-password
```

### 🔑 JWT

```bash
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
```

### 🤖 Telegram

```bash
TELEGRAM_BOT_TOKEN=your-bot-token
TELEGRAM_WEBHOOK_URL=https://your-app.railway.app/telegram/webhook
```

### ⚙️ Application

```bash
ENVIRONMENT=production
SECRET_KEY=your-app-secret-key
DEBUG=false
HOST=0.0.0.0
# PORT jest automatycznie ustawiany przez Railway
```

## 🚀 Deployment w Railway

### 1. Połącz projekt z Railway

```bash
railway login
railway link
```

### 2. Ustaw zmienne środowiskowe

```bash
railway variables set JWT_SECRET_KEY="your-secret-key"
railway variables set REDIS_HOST="your-redis-host"
# ... itd.
```

### 3. Deploy

```bash
railway up
```

## 🔧 Troubleshooting

### Problem: "The asyncio extension requires an async driver"

**Rozwiązanie:** Upewnij się, że `DATABASE_URL` używa `postgresql+asyncpg://` zamiast `postgresql://`

### Problem: "int() argument must be a string, a bytes-like object or a real number, not 'NoneType'"

**Rozwiązanie:** Wszystkie wymagane zmienne środowiskowe muszą być ustawione w Railway

### Problem: Redis connection failed

**Rozwiązanie:** Sprawdź czy Redis service jest dodany do projektu Railway i czy zmienne `REDIS_HOST`, `REDIS_PORT` są poprawnie ustawione

## 📁 Pliki konfiguracyjne

- `railway.env.example` - przykład zmiennych środowiskowych
- `src/config.py` - główna konfiguracja aplikacji
- `.gitignore` - wyklucza pliki `.env` z repozytorium

## 🔒 Bezpieczeństwo

- **NIGDY** nie commituj plików `.env` do Git
- Używaj silnych, unikalnych kluczy sekretnych
- W Railway ustaw `ENVIRONMENT=production` i `DEBUG=false`
- Regularnie rotuj klucze JWT i sekretne klucze aplikacji

# Bills

[![Project Status](https://img.shields.io/badge/status-MVP_in_progress-blue.svg)](./)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](./LICENSE)

## Table of Contents

- [Project name](#bills)
- [Project description](#project-description)
- [Tech stack](#tech-stack)
- [Getting started locally](#getting-started-locally)
- [Available scripts](#available-scripts)
- [Project scope](#project-scope)
- [Project status](#project-status)
- [License](#license)

## Project description

Bills tracks spending from receipt photos. The bot accepts a photo and replies at once that it was received. An ARQ worker runs the read in the background. One Gemini model reads the receipt and, when the catalog is not enough, normalizes the product name. Product-name embeddings live in pgvector, and the prompt receives the recovered catalog. There is a daily cost limit. The app shows the bill and lets the user correct line items, the shop, and the date. There are no multi-step agents, no MCP, and no company document store.

CV line: In my own project, Bills, receipt reading goes through Gemini. Product names are embeddings in pgvector. The normalization prompt receives the recovered catalog. There is a daily cost limit. This is not a client deployment.

Key highlights:

- Telegram accepts a photo and replies that it was received. An ARQ worker processes the bill in the background.
- One Gemini model reads the receipt and, below the catalog threshold, normalizes the name. Product-name embeddings are in pgvector.
- Alias first, then vector search beside pg_trgm. Above the threshold the generative model is not called.
- A daily limit on generative calls and a separate embedding budget. A failed read does not use one of the 100 monthly receipts.
- The app shows the bill and corrects line items, the shop, and the date. Renaming a product stores an alias. Status refreshes by polling.
- Login uses a magic link from the bot.

For full product details, see the PRD:

- PRD (workspace): `.ai/prd.md`

## Tech stack

- Backend:
  - Python 3.14, FastAPI, Uvicorn
  - SQLAlchemy (ORM), Pydantic (validation)
  - python-telegram-bot (Telegram integration)
  - sentry-sdk (logging/monitoring)
  - Supabase (PostgreSQL database, Storage, Auth, migrations)
- Data & AI:
  - Google Gemini: one generative model and one embedding model
  - pgvector and pg_trgm in Postgres
  - LangChain only when building the catalog prompt
  - Redis and an ARQ worker
- Frontend:
  - Astro 5 (static site generation, routing)
  - React 19 (interactive components - Islands Architecture)
  - Tailwind CSS 4 (styling)
  - Shadcn/ui (UI component library)
  - TypeScript 5
- Database & Hosting:
  - Supabase (PostgreSQL, Storage, Authentication)
- Infrastructure:
  - Nginx (reverse proxy, optional)
- Testing:
  - Backend: pytest, pytest-asyncio, pytest-mock, pytest-cov
  - Frontend: Vitest (unit tests), Playwright (E2E tests)
  - Mocking: unittest.mock (Python)

See also: `.ai/tech-stack.md`

## Getting started locally

> Note: This repository may not yet include all service directories or dependency manifests. The steps below provide a sensible local setup for development. Adjust paths and tool choices as needed.

### Prerequisites

- Python 3.14
- Node.js 18+ and npm or pnpm
- Supabase account (or local PostgreSQL 14+)
- OpenAI API key
- Google Gemini API key (for OCR)
- Optional: Sentry DSN (for error tracking)

### Environment variables

Create a `.env` file in the `backend/` directory (or export as environment variables):

```bash
# Application
ENV=development
PORT=8000

# Database (Supabase PostgreSQL)
DATABASE_URL=postgresql+psycopg2://postgres:password@db.xxxxx.supabase.co:5432/postgres

# Supabase (for Storage and Auth)
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key
SUPABASE_STORAGE_BUCKET=bills

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
TELEGRAM_WEBHOOK_URL=https://your-dev-tunnel-or-domain/api/v1/webhooks/telegram
TELEGRAM_WEBHOOK_SECRET=your-webhook-secret-token

# AI Services
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
GEMINI_API_KEY=your-google-gemini-api-key
GEMINI_MODEL=gemini-2.5-flash

# JWT Authentication
JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7
MAGIC_LINK_EXPIRE_MINUTES=30

# Frontend
WEB_APP_URL=http://localhost:4321

# Freemium Limits
MONTHLY_BILLS_LIMIT=100


# Sentry (optional)
SENTRY_DSN=
```

### Backend (FastAPI)

```bash
# 1) Navigate to backend directory
cd backend

# 2) Create and activate virtual environment
python -m venv .venv
# Windows PowerShell:
. .\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

# 3) Install dependencies
uv sync --frozen

# 4) Apply SQL migrations from supabase/migrations
# Local Supabase: supabase migration up --local

# 5) Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Telegram bot

- Set `TELEGRAM_BOT_TOKEN` in `.env`.
- For local development:
  - Either run in polling mode within your bot service, or
  - Expose a public URL for webhooks (e.g., ngrok) and set `TELEGRAM_WEBHOOK_URL`.
- Bot commands in this release: `/start`, `/login`, `/prywatnosc`, plus a receipt photo. The worker command is `arq src.worker.jobs.WorkerSettings`.

### Frontend (Astro + React + Tailwind)

```bash
# 1) Navigate to astro directory
cd astro

# 2) Install dependencies
npm install
# or with pnpm
# pnpm install

# 3) Start development server
npm run dev
# or with pnpm
# pnpm dev

# The frontend will be available at http://localhost:4321
```

### Reverse proxy (optional)

If you need a unified entrypoint, configure Nginx to proxy to:

- FastAPI at `http://localhost:8000`
- Frontend dev server (Astro) at `http://localhost:4321`
- Telegram webhook endpoint mapped to your public URL (`/api/v1/webhooks/telegram`)

## Available scripts

> Adjust to your project structure. If no package/Makefile exists yet, these examples can be added.

- Backend (from `backend/` directory)

  - Start API (dev): `uvicorn main:app --reload --port 8000`
  - Migrations: SQL files in `supabase/migrations` (`supabase migration up --local`)
  - Lint: `uv run ruff check src tests` and `uv run ruff format --check src tests`
  - Tests: `pytest -q`
  - Tests with coverage: `pytest --cov=src --cov-report=html`

- Frontend (from `astro/` directory)
  - Dev: `npm run dev`
  - Build: `npm run build`
  - Preview: `npm run preview`
  - Unit tests: `npm run test` (Vitest)
  - Test UI: `npm run test:ui` (Vitest UI)
  - Test watch: `npm run test:watch`
  - Test coverage: `npm run test:coverage`
  - E2E tests: `npm run test:e2e` (Playwright)
  - E2E UI: `npm run test:e2e:ui`
  - E2E debug: `npm run test:e2e:debug`

## Project scope

In scope (MVP):

- Telegram bot: login, receipt photo, and the accepted-photo reply. Processing runs on the ARQ worker.
- One Gemini model for OCR and for catalog-miss categorization. Product-name embeddings in pgvector.
- Alias, then vector search beside pg_trgm. The generative model is not called above the similarity threshold.
- Daily generative limit and a separate embedding budget.
- Web app: bill status (polled), correction of lines, shop, and date. A renamed product stores an alias.
- The app shows the difference between the line sum and the receipt total. That 20% OCR check stays on the read, not on a user edit.
- Passwordless login via a magic link from the bot.
- Freemium: 100 kept receipts per month. A queued or failed read does not use a slot.

Out of scope (MVP):

- Advanced analytics and forecasting.
- Non-image formats (e.g., PDFs, emails).
- Bulk import of multiple receipts at once.
- Interactive charts/advanced visualizations.
- User-managed categories.
- Group/shared budgets.
- Data export (CSV/Excel, etc.).
- Bank account integrations.
- Multi-currency support.

## Testing

### Backend Tests (pytest)

```bash
# From backend/ directory
cd backend

# Run all tests
pytest

# Tests with coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/example_test.py

# Tests with markers
pytest -m unit
pytest -m integration
```

More information: `backend/tests/README.md`

### Frontend Tests

#### Unit Tests (Vitest)

```bash
# From astro/ directory
cd astro

# Run all tests
npm run test

# Watch mode
npm run test:watch

# UI mode
npm run test:ui

# With coverage
npm run test:coverage
```

#### E2E Tests (Playwright)

```bash
# From the astro/ directory
cd astro

# Run all E2E tests
npm run test:e2e

# UI mode
npm run test:e2e:ui

# Debug mode
npm run test:e2e:debug
```

More information: `astro/src/test/README.md`

## Project status

MVP in progress (~90% complete). Current focus:

- ✅ OCR Service (LLM-based with Gemini API) - **Completed**
- ✅ Telegram Bot - receipt image upload and Bill creation - **Completed**
- ✅ User isolation and rate limiting - **Completed**
- ✅ Storage Service (Supabase) - **Completed**
- ✅ Receipt Processing Pipeline (OCR → AI → Database) - **Completed**
- ✅ AI Categorization Service (normalization, Product Index mapping) - **Completed**
- ✅ Reports module (daily/weekly/monthly summaries) - **Completed**
- ✅ Verification workflow (BillVerificationService) - **Completed**
- 🟢 Admin endpoints - **Planned (Nice to have)**
- 🟢 Security enhancements - **Planned (Nice to have)**

Success metrics:

- 90% of items correctly processed automatically (OCR, normalization, categorization)
- <10% of items require manual verification

For detailed progress, see: `PLAN_AKTUALIZACJA.md`

## License

MIT (to be confirmed). If you intend to use a different license, add a `LICENSE` file and update the badge above accordingly.

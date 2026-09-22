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

Bills automates personal expense tracking by letting users send receipt photos to a Telegram bot. The system uses OCR to extract line items, applies AI to normalize and categorize products, validates the sum against the receipt total, and stores the data for summaries. A read‑only web app complements the bot with clear summaries and a passwordless “magic link” login delivered by the bot.

Key highlights:

- Capture receipts via Telegram; instant confirmation and processing.
- OCR with high‑quality text extraction; AI normalization and categorization to predefined categories, with fallback to “Other”.
- Low‑confidence items can be confirmed by the user directly in the bot.
- Text summaries available in the bot (daily/weekly/monthly).
- Read‑only web app for visual summaries; login via one‑time magic link.
- Freemium plan: up to 100 receipts per month; warnings at 90; blocks at 101 with reset info.
- Privacy by design: avoid processing personal data from receipts; simple privacy policy accessible in the bot.

For full product details, see the PRD:

- PRD (workspace): `.ai/prd.md`

## Tech stack

- Backend:
  - Python 3.13, FastAPI, Uvicorn
  - SQLAlchemy (ORM), Pydantic (validation)
  - python-telegram-bot (Telegram integration)
  - sentry-sdk (logging/monitoring)
  - Supabase (PostgreSQL database, Storage, Auth, migrations)
- Data & AI:
  - **OCR (MVP):** Google Gemini API (Gemini 1.5 Flash) - LLM-based extraction
  - **OCR (Post-MVP):** PaddlePaddle-OCR (planned for future improvements)
  - OpenAI API (categorization & normalization)
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

- Python 3.13
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
pip install -r requirements.txt

# 4) Run database migrations (Alembic)
alembic upgrade head

# 5) Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Telegram bot

- Set `TELEGRAM_BOT_TOKEN` in `.env`.
- For local development:
  - Either run in polling mode within your bot service, or
  - Expose a public URL for webhooks (e.g., ngrok) and set `TELEGRAM_WEBHOOK_URL`.
- Commands supported by MVP (as per PRD): `/start`, `/dzis`, `/tydzien`, `/miesiac`, `/login`, `/prywatnosc`.

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
  - Run migrations: `alembic upgrade head`
  - Generate migration: `alembic revision --autogenerate -m "message"`
  - Lint (example): `ruff check .` or `flake8`
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

- Telegram bot to accept receipt photos and simple text commands.
- OCR extraction of line items (using Gemini API for MVP).
- AI-based normalization and categorization into predefined categories; low-confidence items go through user confirmation.
- Receipt total validation versus sum of items.
- Text summaries in the bot: daily, weekly, monthly.
- Read-only web app with the same summaries as in the bot.
- Passwordless login to the web app via bot-provided magic link.
- Freemium model: 100 receipts/month; notify at 90; block at 101; show reset date.
- Privacy policy available through a bot command; avoid processing personal data from receipts.

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
# Z katalogu astro/
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

# Playwright

One spec: a magic link issued into the Compose Postgres logs in through the real frontend and API, then opens the bills list. The list does not create a receipt.

The seed script talks to `TEST_DATABASE_URL` (default `127.0.0.1:5433`). The API process must use that same database. Telegram, OCR, and the categorization model are not called.

```bash
npx playwright test e2e/tests/auth.spec.ts
```

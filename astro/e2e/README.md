# E2E Tests for Bills Application

This directory contains End-to-End tests using Playwright for the Bills application.

## Structure

```
e2e/
  ├── page-objects/       # Page Object Model classes
  │   └── AuthPage.ts     # Authentication page object
  ├── fixtures/            # Test helpers and utilities
  │   ├── auth-helpers.ts  # Authentication helper functions
  │   └── test-data.ts     # Test data and fixtures
  ├── tests/               # Test specifications
  │   └── auth.spec.ts     # Authentication E2E tests
  └── README.md            # This file
```

## Prerequisites

1. **Backend API must be running**

   - Default: `http://localhost:8000/api/v1`
   - Can be configured via `BACKEND_URL` environment variable

2. **Frontend dev server**

   - Will be started automatically by Playwright (configured in `playwright.config.ts`)
   - Default: `http://localhost:4321`

3. **Test database**
   - Should have test users with known `telegram_user_id`
   - Magic links can be generated for these users
   - Configure test user via `TELEGRAM_TEST_USER` environment variable in `.env` file:
     ```bash
     TELEGRAM_TEST_USER=123456789
     ```
   - Or edit `TEST_USER.external_id` in `e2e/fixtures/test-data.ts`

## Running Tests

### Run all E2E tests

```bash
npm run test:e2e
```

### Run tests in UI mode (interactive)

```bash
npm run test:e2e:ui
```

### Run tests in debug mode

```bash
npm run test:e2e:debug
```

### Run specific test file

```bash
npx playwright test e2e/tests/auth.spec.ts
```

### Run tests in headed mode (see browser)

```bash
npx playwright test --headed
```

## Test Setup

### Authentication Tests

The authentication tests (`auth.spec.ts`) test the magic link authentication flow. To run these tests successfully:

1. **Set up test user in database:**

   ```sql
   -- Example: Create a test user
   -- Replace 123456789 with your actual test user's telegram_user_id
   INSERT INTO users (external_id, is_active)
   VALUES (123456789, true);
   ```

2. **Configure test user ID:**

   **Option A: Environment variable in .env file (recommended)**

   Add to your `.env` file:

   ```bash
   TELEGRAM_TEST_USER=123456789
   ```

   **Option B: Edit test-data.ts**

   ```typescript
   // In e2e/fixtures/test-data.ts
   export const TEST_USER: TestUser = {
     external_id: 123456789, // Your test user's telegram_user_id
     // ...
   };
   ```

3. **Generate magic link token:**

   ```bash
   # Via API (example)
   curl -X POST http://localhost:8000/api/v1/auth/magic-link \
     -H "Content-Type: application/json" \
     -d '{"telegram_user_id": 123456789}'
   ```

4. **Extract token from response:**
   - The response contains a `magic_link` URL
   - Extract the `token` query parameter from the URL
   - Use this token in your tests

### Updating Tests with Real Tokens

Currently, the tests use placeholder tokens like `'test-valid-token'`. To use real tokens:

1. **Option 1: Use test fixtures (Recommended)**

   ```typescript
   import { generateTestMagicLink, TEST_USER } from '../fixtures/test-data';

   test('should verify valid token', async ({ page }) => {
     // This will automatically call the backend API to generate a token
     const token = await generateTestMagicLink(TEST_USER.external_id);
     await authPage.gotoVerify(token);
     // ... rest of test
   });
   ```

   **Note:** This requires:

   - Backend API to be running
   - Test user to exist in database with `telegram_user_id = TEST_USER.external_id`

2. **Option 2: Use environment variables**

   ```typescript
   const validToken = process.env.TEST_MAGIC_LINK_TOKEN || 'test-valid-token';
   ```

3. **Option 3: Use Playwright fixtures**
   ```typescript
   // In playwright.config.ts or separate fixture file
   test.extend({
     magicLinkToken: async ({}, use) => {
       const token = await generateTestMagicLink(TEST_USER.external_id);
       await use(token);
     },
   });
   ```

## Test Coverage

### Authentication Tests (`auth.spec.ts`)

✅ **Successful Authentication Flow**

- Valid token verification
- Session management (localStorage + cookies)
- Redirect to dashboard

✅ **Error Handling**

- Invalid token
- Expired token
- Missing token
- Already used token

✅ **Redirects and Navigation**

- Redirect to dashboard after success
- Redirect unauthenticated users

✅ **Session Management**

- Session persistence across reloads
- Session clearing on logout

✅ **Token Refresh**

- Automatic token refresh on 401 (basic setup)

## Best Practices

1. **Use Page Object Model**: All page interactions should go through Page Objects
2. **Isolate tests**: Each test should be independent and clean up after itself
3. **Use data-testid**: When adding new UI elements, use `data-testid` attributes for reliable selectors
4. **Wait for elements**: Always wait for elements to be visible/ready before interacting
5. **Clean up**: Clear sessions and test data after tests

## Debugging

### View test execution

```bash
npm run test:e2e:ui
```

### Debug specific test

```bash
npx playwright test auth.spec.ts --debug
```

### View trace

After a test fails, you can view the trace:

```bash
npx playwright show-trace trace.zip
```

### Screenshots and videos

Failed tests automatically capture:

- Screenshot (in `test-results/`)
- Video (in `test-results/`)
- Trace (if enabled)

## CI/CD Integration

Tests are configured to:

- Run in parallel when possible
- Retry failed tests (2 retries in CI)
- Generate HTML reports
- Capture traces on failure

## Notes

- Tests require both frontend and backend to be running
- Some tests may need actual database setup (for generating real tokens)
- Consider using test containers or test database for CI/CD
- Mock external services (OCR, AI) to keep tests fast and reliable

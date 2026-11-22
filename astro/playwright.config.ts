import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for Bills E2E tests
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  
  // Maximum time one test can run for
  timeout: 30 * 1000,
  
  // Test execution
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  
  // Reporter configuration
  reporter: [
    ['html'],
    ['list'],
    process.env.CI ? ['github'] : ['list'],
  ],
  
  // Shared settings for all projects
  use: {
    // Base URL for tests
    baseURL: 'http://localhost:4321',
    
    // Collect trace when retrying the failed test
    trace: 'on-first-retry',
    
    // Screenshot on failure
    screenshot: 'only-on-failure',
    
    // Video on failure
    video: 'retain-on-failure',
  },

  // Trio Chromium, Firefox, Edge.
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'msedge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
    },
  ],

  // Run local dev server before starting tests
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:4321',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});


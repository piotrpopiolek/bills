/**
 * Test data and fixtures for E2E tests
 * 
 * This module provides utilities for:
 * 1. Loading a magic link token issued by the Telegram /login command
 * 2. Managing test user data
 * 3. Extracting tokens from URLs
 * 
 * Requirements:
 * - Backend API must be running (default: http://localhost:8000/api/v1)
 * - Test user must exist in database with matching telegram_user_id
 * - BACKEND_URL environment variable can be set to override default
 */

export interface TestUser {
  id: number;
  external_id: number;
  is_active: boolean;
  created_at: string;
}

export interface TestTokens {
  access_token: string;
  refresh_token: string;
  user: TestUser;
}

/**
 * Test user data for E2E tests
 * 
 * The external_id (telegram_user_id) can be configured via:
 * 1. Environment variable TELEGRAM_TEST_USER (from .env file, recommended)
 * 2. Hardcoded value below (for local development)
 * 
 * Make sure the user with this telegram_user_id exists in your test database.
 */
export const TEST_USER: TestUser = {
  id: 1,
  external_id: process.env.TELEGRAM_TEST_USER 
    ? parseInt(process.env.TELEGRAM_TEST_USER, 10) 
    : 123456789, // Default example value - replace with your test user's telegram_user_id
  is_active: true,
  created_at: new Date().toISOString(),
};

/**
 * Get backend URL from environment variable or use default
 */
function getBackendUrl(): string {
  // In Playwright tests, we can use process.env
  // Default to localhost:8000/api/v1
  const backendUrl = process.env.BACKEND_URL || process.env.PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  
  // Ensure URL includes /api/v1 prefix
  if (backendUrl.endsWith('/api/v1')) {
    return backendUrl;
  } else if (backendUrl.endsWith('/api/v1/')) {
    return backendUrl.slice(0, -1);
  } else {
    return `${backendUrl}/api/v1`;
  }
}

/**
 * Check if backend API is accessible
 * 
 * @returns Promise that resolves to true if backend is accessible, false otherwise
 * 
 * @example
 * ```typescript
 * const isAvailable = await checkBackendAvailability();
 * if (!isAvailable) {
 *   throw new Error('Backend is not running');
 * }
 * ```
 */
export async function checkBackendAvailability(): Promise<boolean> {
  try {
    const backendUrl = getBackendUrl();
    // Try to access a simple endpoint (health check or similar)
    // For now, we'll just try to connect
    const response = await fetch(`${backendUrl}/auth/magic-link`, {
      method: 'GET',
    });
    // Any response (even 404) means server is up
    return true;
  } catch {
    return false;
  }
}

/**
 * Magic links are not minted over HTTP.
 * Callers should use TEST_MAGIC_LINK_TOKEN from the Telegram /login command.
 * This function always fails so tests skip instead of calling a public issuer.
 */
export async function generateTestMagicLink(
  _telegramUserId: number,
  _redirectUrl?: string
): Promise<string> {
  throw new Error(
    "Login links are issued only by the Telegram /login command. " +
      "Set TEST_MAGIC_LINK_TOKEN to a token from that flow."
  );
}

/**
 * Extract token from magic link URL
 * 
 * @param magicLinkUrl - Full magic link URL (e.g., "https://app.com/auth/verify?token=abc123")
 * @returns Extracted token string
 * 
 * @throws Error if token is not found in URL
 * 
 * @example
 * ```typescript
 * const token = extractTokenFromUrl('https://app.com/auth/verify?token=abc123');
 * // Returns: 'abc123'
 * ```
 */
export function extractTokenFromUrl(magicLinkUrl: string): string {
  try {
    const url = new URL(magicLinkUrl);
    const token = url.searchParams.get('token');
    
    if (!token) {
      throw new Error(
        `Token not found in magic link URL: ${magicLinkUrl}. ` +
        `Expected format: https://domain.com/auth/verify?token=<token>`
      );
    }
    
    return token;
  } catch (error) {
    if (error instanceof TypeError) {
      throw new Error(
        `Invalid magic link URL format: ${magicLinkUrl}. ` +
        `Original error: ${error.message}`
      );
    }
    throw error;
  }
}

/**
 * Helper to create a test user via API
 * This should be called in test setup
 */
export async function createTestUser(telegramUserId: number): Promise<TestUser> {
  // Placeholder - implement with actual API call
  throw new Error('createTestUser must be implemented with actual API call');
}

/**
 * Helper to clean up test user
 * This should be called in test teardown
 */
export async function deleteTestUser(userId: number): Promise<void> {
  // Placeholder - implement with actual API call
  throw new Error('deleteTestUser must be implemented with actual API call');
}

import { Page } from '@playwright/test';

/**
 * Magic-link verification screen.
 */
export class AuthPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async gotoVerify(token: string): Promise<void> {
    await this.page.goto(`/auth/verify?token=${encodeURIComponent(token)}`);
  }

  heading() {
    return this.page.getByRole('heading', { name: 'Weryfikacja...' });
  }
}

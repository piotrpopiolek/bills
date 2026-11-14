import { Page } from '@playwright/test';

/**
 * Read-only bills list.
 */
export class BillsPage {
  readonly page: Page;

  constructor(page: Page) {
    this.page = page;
  }

  async goto(): Promise<void> {
    await this.page.goto('/bills');
  }

  heading() {
    return this.page.getByRole('heading', { name: 'Lista Paragonów' });
  }

  amount(text: string) {
    return this.page.getByRole('cell', { name: text });
  }

  createControl() {
    return this.page.getByRole('button', {
      name: /dodaj paragon|nowy paragon|prześlij paragon/i,
    });
  }
}

import { describe, expect, it } from 'vitest';

import { receiptShop } from './BillMetadata';

describe('receiptShop', () => {
  it('links a shop from shop_id and shop_name when the nested shop is absent', () => {
    expect(
      receiptShop({
        id: 1,
        bill_date: '2026-11-01',
        status: 'completed',
        created_at: '2026-11-01T00:00:00Z',
        total_amount: '10.00',
        shop_id: 4,
        shop_name: 'dino polska s.a.',
      })
    ).toEqual({ id: 4, name: 'dino polska s.a.' });
  });

  it('keeps a name without an id as plain text', () => {
    expect(
      receiptShop({
        id: 1,
        bill_date: '2026-11-01',
        status: 'completed',
        created_at: '2026-11-01T00:00:00Z',
        total_amount: null,
        shop_name: 'aldi',
      }).id
    ).toBeNull();
  });
});

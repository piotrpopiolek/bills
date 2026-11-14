import { describe, expect, it } from 'vitest';

import type { CategoryResponse } from '@/types';

import { buildCategoryTree } from './category-tree';

const CREATED_AT = '2026-01-15T00:00:00.000Z';

function category(
  id: number,
  name: string,
  parentId: number | null
): CategoryResponse {
  return {
    id,
    name,
    parent_id: parentId,
    created_at: CREATED_AT,
    children: [],
    products_count: 0,
    bill_items_count: 0,
  };
}

describe('buildCategoryTree', () => {
  it('returns no roots for an empty list', () => {
    expect(buildCategoryTree([])).toEqual([]);
  });

  it('nests children under their parent and sorts the children by name', () => {
    const tree = buildCategoryTree([
      category(1, 'Jedzenie', null),
      category(3, 'Pieczywo', 1),
      category(2, 'Mleko', 1),
    ]);

    expect(tree.map((node) => node.name)).toEqual(['Jedzenie']);
    expect(tree[0]?.children.map((node) => node.name)).toEqual(['Mleko', 'Pieczywo']);
    expect(tree[0]?.children[0]?.parent_id).toBe(1);
  });

  it('keeps root categories in input order', () => {
    const tree = buildCategoryTree([
      category(2, 'Żywność', null),
      category(1, 'Dom', null),
    ]);

    expect(tree.map((node) => node.name)).toEqual(['Żywność', 'Dom']);
  });

  it('treats a category with a missing parent as a root', () => {
    const tree = buildCategoryTree([category(4, 'Sierota', 99)]);

    expect(tree.map((node) => node.id)).toEqual([4]);
    expect(tree[0]?.children).toEqual([]);
  });
});

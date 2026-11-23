import { describe, expect, it } from 'vitest';
import { sumDifference } from './sum-difference';

describe('sumDifference', () => {
  it('returns how far the lines are from the receipt total', () => {
    expect(sumDifference(12.5, 10)).toBe(2.5);
    expect(sumDifference(9.5, 10)).toBe(-0.5);
  });

  it('returns null when the receipt total is missing', () => {
    expect(sumDifference(4, null)).toBeNull();
    expect(sumDifference(Number.NaN, 4)).toBeNull();
  });
});
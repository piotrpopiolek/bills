import { describe, expect, it } from 'vitest';

import {
  calculateTrend,
  calendarDateInput,
  formatCurrency,
  formatDate,
  formatShopName,
  getPreviousMonth,
  parseAmount,
} from './formatting';

describe('formatCurrency', () => {
  it.each([
    { amount: 12.5, currency: undefined, expected: '12.50 PLN', id: 'two-decimals' },
    { amount: 0, currency: undefined, expected: '0.00 PLN', id: 'zero' },
    { amount: null, currency: undefined, expected: '0.00 PLN', id: 'null' },
    { amount: undefined, currency: undefined, expected: '0.00 PLN', id: 'undefined' },
    { amount: Number.NaN, currency: undefined, expected: '0.00 PLN', id: 'nan' },
    { amount: 3, currency: 'EUR', expected: '3.00 EUR', id: 'other-currency' },
  ])('$id', ({ amount, currency, expected }) => {
    const formatted =
      currency === undefined ? formatCurrency(amount) : formatCurrency(amount, currency);
    expect(formatted).toBe(expected);
  });
});

describe('calendarDateInput', () => {
  it('uses the local calendar day rather than the UTC date prefix', () => {
    const iso = '2026-11-23T23:30:00.000Z';
    const date = new Date(iso);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const localDay = `${date.getFullYear()}-${month}-${day}`;

    expect(calendarDateInput(iso)).toBe(localDay);
    if (localDay !== iso.slice(0, 10)) {
      expect(calendarDateInput(iso)).not.toBe(iso.slice(0, 10));
    }
  });
});

describe('formatDate', () => {
  it('formats a local calendar date as DD.MM.YYYY', () => {
    expect(formatDate(new Date(2024, 0, 15))).toBe('15.01.2024');
  });

  it('returns an empty string for an invalid date', () => {
    expect(formatDate('not-a-date')).toBe('');
  });
});

describe('formatShopName', () => {
  it.each([
    { name: 'dino polska s.a.', expected: 'Dino Polska S.A.' },
    { name: 'aldi sp. z o.o.', expected: 'Aldi Sp. Z O.O.' },
    { name: null, expected: 'Nieznany sklep' },
    { name: undefined, expected: 'Nieznany sklep' },
    { name: '', expected: 'Nieznany sklep' },
  ])('$name -> $expected', ({ name, expected }) => {
    expect(formatShopName(name)).toBe(expected);
  });
});

describe('calculateTrend', () => {
  it('returns null when the previous value is zero', () => {
    expect(calculateTrend(10, 0)).toBeNull();
  });

  it('reports the absolute percent change and its direction', () => {
    expect(calculateTrend(150, 100)).toEqual({ value: 50, isPositive: true });
    expect(calculateTrend(50, 100)).toEqual({ value: 50, isPositive: false });
  });
});

describe('parseAmount', () => {
  it.each([
    { amount: null, expected: 0 },
    { amount: undefined, expected: 0 },
    { amount: '12.50', expected: 12.5 },
    { amount: 'nie-liczba', expected: 0 },
    { amount: 4, expected: 4 },
  ])('$amount -> $expected', ({ amount, expected }) => {
    expect(parseAmount(amount)).toBe(expected);
  });
});

describe('getPreviousMonth', () => {
  it.each([
    { month: '2026-03', expected: '2026-02' },
    { month: '2026-01', expected: '2025-12' },
  ])('$month -> $expected', ({ month, expected }) => {
    expect(getPreviousMonth(month)).toBe(expected);
  });
});

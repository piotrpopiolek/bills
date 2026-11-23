export function sumDifference(
  itemsSum: number,
  receiptTotal: number | null,
): number | null {
  if (receiptTotal === null || Number.isNaN(receiptTotal) || Number.isNaN(itemsSum)) {
    return null;
  }
  return Math.round((itemsSum - receiptTotal) * 100) / 100;
}

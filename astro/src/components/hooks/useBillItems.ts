import { useState, useEffect, useCallback } from 'react';
import type { BillItemResponse } from '@/types';
import { getBillItems } from '@/lib/services/bills';

interface UseBillItemsReturn {
  items: BillItemResponse[];
  total: number;
  limit: number;
  isLoading: boolean;
  error: Error | null;
  itemsSum: number | string | null;
  skip: number;
  setSkip: (skip: number) => void;
  refetch: () => Promise<void>;
}

export const useBillItems = (
  billId: number,
  initialSkip: number = 0,
  initialLimit: number = 100
): UseBillItemsReturn => {
  const [items, setItems] = useState<BillItemResponse[]>([]);
  const [itemsSum, setItemsSum] = useState<number | string | null>(null);
  const [total, setTotal] = useState<number>(0);
  const [limit, setLimit] = useState<number>(initialLimit);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<Error | null>(null);

  const [skip, setSkip] = useState<number>(initialSkip);

  // Fetch data
  const fetchData = useCallback(async () => {
    if (!billId || billId <= 0) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      const response = await getBillItems(billId, {
        skip,
        limit: initialLimit,
      });

      setItems(response.items || []);
      setItemsSum(response.items_sum ?? null);
      setTotal(response.total || 0);
      setLimit(response.limit || initialLimit);
    } catch (err) {
      console.error('useBillItems error:', err);
      setError(
        err instanceof Error ? err : new Error('An unknown error occurred')
      );
      setItems([]);
      setItemsSum(null);
      setTotal(0);
    } finally {
      setIsLoading(false);
    }
  }, [billId, skip, initialLimit]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return {
    items,
    itemsSum,
    total,
    limit,
    isLoading,
    error,
    skip,
    setSkip,
    refetch: fetchData,
  };
};


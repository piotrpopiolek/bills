import React, { useEffect, useState } from 'react';
import type { BillResponse, ShopResponse } from '@/types';
import { BillStatusBadge } from '../BillStatusBadge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ExternalLink } from 'lucide-react';
import { calendarDateInput, formatShopName } from '@/lib/utils/formatting';

export function receiptShop(bill: BillResponse): {
  id: number | null;
  name: string | null;
} {
  return {
    id: bill.shop_id ?? bill.shop?.id ?? null,
    name: bill.shop_name || bill.shop?.name || null,
  };
}

interface BillMetadataProps {
  bill: BillResponse;
  shops: ShopResponse[];
  onShopClick?: (shopId: number) => void;
  onSave: (patch: {
    bill_date?: string;
    shop_id?: number;
    shop_name?: string;
  }) => Promise<void>;
}

export const BillMetadata: React.FC<BillMetadataProps> = ({
  bill,
  shops,
  onShopClick,
  onSave,
}) => {
  const savedDate = calendarDateInput(bill.bill_date);
  const [billDate, setBillDate] = useState(savedDate);
  const [shopId, setShopId] = useState(bill.shop_id ? String(bill.shop_id) : '');
  const [shopName, setShopName] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  useEffect(() => {
    setBillDate(savedDate);
  }, [savedDate]);
  // Format date
  const formatDate = (dateString: string): string => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('pl-PL', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateString;
    }
  };

  // Format amount
  const formatAmount = (amount: number | string | null): string => {
    if (amount === null || amount === undefined) {
      return 'Przetwarzanie...';
    }
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numAmount)) {
      return '-';
    }
    return `${numAmount.toFixed(2)} PLN`;
  };

  // Handle shop click
  const handleShopClick = (shopId: number) => {
    if (onShopClick) {
      onShopClick(shopId);
    } else {
      // Default navigation
      window.location.href = `/shops/${shopId}`;
    }
  };

  const shop = receiptShop(bill);
  const linkedShopId = shop.id;

  return (
    <div className="rounded-md border p-4">
      <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <dt className="text-sm font-medium text-muted-foreground mb-1">
            Data
          </dt>
          <dd className="space-y-2">
            <p className="text-sm font-medium">
              {bill.bill_date ? formatDate(bill.bill_date) : 'Brak daty'}
            </p>
            <Input
              type="date"
              aria-label="Data paragonu"
              value={billDate}
              onChange={(event) => setBillDate(event.target.value)}
            />
          </dd>
        </div>

        <div>
          <dt className="text-sm font-medium text-muted-foreground mb-1">
            Sklep
          </dt>
          <dd>
            {shop.name && linkedShopId != null ? (
              <Button
                variant="link"
                className="h-auto p-0 text-sm font-medium"
                onClick={() => handleShopClick(linkedShopId)}
              >
                {formatShopName(shop.name)}
                <ExternalLink className="ml-1 h-3 w-3" />
              </Button>
            ) : shop.name ? (
              <span className="text-sm font-medium">{formatShopName(shop.name)}</span>
            ) : (
              <span className="text-sm text-muted-foreground">
                Nieznany sklep
              </span>
            )}
            <div className="mt-2 space-y-2">
              <select
                aria-label="Wybierz sklep"
                className="h-9 w-full rounded-md border bg-transparent px-3 text-sm"
                value={shopId}
                onChange={(event) => setShopId(event.target.value)}
              >
                <option value="">Wybierz istniejący</option>
                {shops.map((shop) => (
                  <option key={shop.id} value={shop.id}>
                    {formatShopName(shop.name)}
                  </option>
                ))}
              </select>
              <Input
                aria-label="Nowa nazwa sklepu"
                placeholder="Albo wpisz nazwę sklepu"
                value={shopName}
                onChange={(event) => setShopName(event.target.value)}
              />
            </div>
          </dd>
        </div>

        <div>
          <dt className="text-sm font-medium text-muted-foreground mb-1">
            Suma
          </dt>
          <dd className="text-sm font-medium">{formatAmount(bill.total_amount)}</dd>
        </div>

        <div>
          <dt className="text-sm font-medium text-muted-foreground mb-1">
            Status
          </dt>
          <dd>
            <BillStatusBadge status={bill.status} />
          </dd>
        </div>
      </dl>
      {saveError && <p className="mt-3 text-sm text-destructive">{saveError}</p>}
      <Button
        type="button"
        className="mt-4"
        disabled={saving}
        onClick={() => {
          setSaveError(null);
          setSaving(true);
          const patch: { bill_date?: string; shop_id?: number; shop_name?: string } = {};
          if (billDate) {
            patch.bill_date = billDate;
          }
          if (shopName.trim()) {
            patch.shop_name = shopName.trim();
          } else if (shopId) {
            patch.shop_id = Number(shopId);
          }
          void onSave(patch)
            .catch((error: unknown) => {
              setSaveError(error instanceof Error ? error.message : 'Nie udało się zapisać');
            })
            .finally(() => setSaving(false));
        }}
      >
        Zapisz sklep i datę
      </Button>
    </div>
  );
};

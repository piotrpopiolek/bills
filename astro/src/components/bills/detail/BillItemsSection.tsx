import React, { useMemo, useState } from 'react';
import type { BillItemResponse } from '@/types';
import { BillItemsTable } from './BillItemsTable';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { sumDifference } from '@/lib/bills/sum-difference';
import type { ItemWrite } from '@/lib/services/bills';

interface BillItemsSectionProps {
  items: BillItemResponse[];
  isLoading: boolean;
  totalAmount: number | string | null;
  onSaveItem: (itemId: number, patch: ItemWrite) => Promise<void>;
  onCreateItem: (item: Required<ItemWrite>) => Promise<void>;
  onDeleteItem: (itemId: number) => Promise<void>;
}

export const BillItemsSection: React.FC<BillItemsSectionProps> = ({
  items,
  isLoading,
  totalAmount,
  onSaveItem,
  onCreateItem,
  onDeleteItem,
}) => {
  const [draft, setDraft] = useState({ name: '', quantity: '1', unitPrice: '', totalPrice: '' });
  const [editing, setEditing] = useState<BillItemResponse | null>(null);
  const [editDraft, setEditDraft] = useState({ name: '', quantity: '', unitPrice: '', totalPrice: '' });
  const [formError, setFormError] = useState<string | null>(null);
  // Calculate sum of all items
  const itemsSum = useMemo(() => {
    if (!items || items.length === 0) {
      return 0;
    }
    return items.reduce((sum, item) => {
      const price = parseFloat(item.total_price);
      return sum + (isNaN(price) ? 0 : price);
    }, 0);
  }, [items]);

  // Format amount
  const formatAmount = (amount: number | string | null): string => {
    if (amount === null || amount === undefined) {
      return '-';
    }
    const numAmount = typeof amount === 'string' ? parseFloat(amount) : amount;
    if (isNaN(numAmount)) {
      return '-';
    }
    return `${numAmount.toFixed(2)} PLN`;
  };

  const receiptTotal = useMemo(() => {
    if (totalAmount === null || totalAmount === undefined) {
      return null;
    }
    const parsed = typeof totalAmount === 'string' ? parseFloat(totalAmount) : totalAmount;
    return Number.isNaN(parsed) ? null : parsed;
  }, [totalAmount]);
  const difference = sumDifference(itemsSum, receiptTotal);

  const startEdit = (item: BillItemResponse) => {
    setEditing(item);
    setEditDraft({
      name: item.index_name || item.original_text || '',
      quantity: item.quantity,
      unitPrice: item.unit_price,
      totalPrice: item.total_price,
    });
    setFormError(null);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">
          Pozycje paragonu ({items.length})
        </h2>
      </div>

      <form
        className="grid gap-2 md:grid-cols-5"
        onSubmit={(event) => {
          event.preventDefault();
          setFormError(null);
          void onCreateItem({
            name: draft.name,
            quantity: Number(draft.quantity),
            unit_price: Number(draft.unitPrice),
            total_price: Number(draft.totalPrice),
          }).then(() => {
            setDraft({ name: '', quantity: '1', unitPrice: '', totalPrice: '' });
          }).catch((error: unknown) => {
            setFormError(error instanceof Error ? error.message : 'Nie udało się dodać pozycji');
          });
        }}
      >
        <Input
          aria-label="Nazwa nowej pozycji"
          placeholder="Nazwa produktu"
          value={draft.name}
          onChange={(event) => setDraft({ ...draft, name: event.target.value })}
          required
        />
        <Input
          aria-label="Ilość"
          inputMode="decimal"
          value={draft.quantity}
          onChange={(event) => setDraft({ ...draft, quantity: event.target.value })}
          required
        />
        <Input
          aria-label="Cena jednostkowa"
          inputMode="decimal"
          placeholder="Cena jedn."
          value={draft.unitPrice}
          onChange={(event) => setDraft({ ...draft, unitPrice: event.target.value })}
          required
        />
        <Input
          aria-label="Cena całkowita"
          inputMode="decimal"
          placeholder="Cena całk."
          value={draft.totalPrice}
          onChange={(event) => setDraft({ ...draft, totalPrice: event.target.value })}
          required
        />
        <Button type="submit">Dodaj pozycję</Button>
      </form>

      {editing && (
        <form
          className="grid gap-2 md:grid-cols-5"
          onSubmit={(event) => {
            event.preventDefault();
            setFormError(null);
            void onSaveItem(editing.id, {
              name: editDraft.name,
              quantity: Number(editDraft.quantity),
              unit_price: Number(editDraft.unitPrice),
              total_price: Number(editDraft.totalPrice),
            }).then(() => setEditing(null)).catch((error: unknown) => {
              setFormError(error instanceof Error ? error.message : 'Nie udało się zapisać pozycji');
            });
          }}
        >
          <Input
            aria-label="Nazwa pozycji"
            value={editDraft.name}
            onChange={(event) => setEditDraft({ ...editDraft, name: event.target.value })}
            required
          />
          <Input
            aria-label="Ilość pozycji"
            value={editDraft.quantity}
            onChange={(event) => setEditDraft({ ...editDraft, quantity: event.target.value })}
            required
          />
          <Input
            aria-label="Cena jednostkowa pozycji"
            value={editDraft.unitPrice}
            onChange={(event) => setEditDraft({ ...editDraft, unitPrice: event.target.value })}
            required
          />
          <Input
            aria-label="Cena całkowita pozycji"
            value={editDraft.totalPrice}
            onChange={(event) => setEditDraft({ ...editDraft, totalPrice: event.target.value })}
            required
          />
          <Button type="submit">Zapisz pozycję</Button>
        </form>
      )}
      {formError && <p className="text-sm text-destructive">{formError}</p>}

      <BillItemsTable
        items={items}
        isLoading={isLoading}
        onEdit={startEdit}
        onDelete={(item) => {
          setFormError(null);
          void onDeleteItem(item.id).catch((error: unknown) => {
            setFormError(error instanceof Error ? error.message : 'Nie udało się usunąć pozycji');
          });
        }}
      />

      {!isLoading && items.length > 0 && (
        <div className="flex flex-col items-end gap-2">
          <div className="text-right">
            <span className="text-sm text-muted-foreground">Suma pozycji: </span>
            <span className="font-medium">{formatAmount(itemsSum)}</span>
          </div>
          {totalAmount !== null && totalAmount !== undefined && (
            <>
              <div className="text-right">
                <span className="text-sm text-muted-foreground">Suma paragonu: </span>
                <span className="font-medium">{formatAmount(totalAmount)}</span>
              </div>
              {difference !== null && Math.abs(difference) >= 0.01 && (
                <div className="text-right text-sm text-yellow-600 dark:text-yellow-400">
                  Różnica: {formatAmount(difference)}
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

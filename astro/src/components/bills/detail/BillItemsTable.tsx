import React from 'react';
import type { BillItemResponse } from '@/types';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Skeleton } from '@/components/ui/skeleton';
import { ConfidenceIndicator } from './ConfidenceIndicator';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { Check, Pencil, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface BillItemsTableProps {
  items: BillItemResponse[];
  isLoading: boolean;
  onEdit?: (item: BillItemResponse) => void;
  onDelete?: (item: BillItemResponse) => void;
}

export const BillItemsTable: React.FC<BillItemsTableProps> = ({
  items,
  isLoading,
  onEdit,
  onDelete,
}) => {
  // Format number from string, removing trailing zeros
  const formatNumber = (value: string): string => {
    const num = parseFloat(value);
    if (isNaN(num)) {
      return value;
    }
    // Remove trailing zeros
    return num.toString();
  };

  // Format price
  const formatPrice = (value: string): string => {
    const num = parseFloat(value);
    if (isNaN(num)) {
      return value;
    }
    return `${num.toFixed(2)} PLN`;
  };

  // Format verification source label
  const formatVerificationSource = (source: string): string => {
    const sourceMap: Record<string, string> = {
      auto: 'Automatyczna',
      user: 'Użytkownik',
      admin: 'Administrator',
    };
    return sourceMap[source] || source;
  };

  if (isLoading) {
    return (
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Nazwa produktu</TableHead>
              <TableHead className="hidden md:table-cell">Kategoria</TableHead>
              <TableHead className="hidden md:table-cell">Tekst oryginalny</TableHead>
              <TableHead className="hidden md:table-cell">Ilość</TableHead>
              <TableHead className="hidden md:table-cell">Cena jednostkowa</TableHead>
              <TableHead className="text-right">Cena całkowita</TableHead>
              <TableHead>Pewność</TableHead>
              <TableHead className="hidden md:table-cell">Status</TableHead>
              <TableHead>Akcje</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {Array.from({ length: 5 }).map((_, index) => (
              <TableRow key={index}>
                <TableCell>
                  <Skeleton className="h-4 w-[200px]" />
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <Skeleton className="h-4 w-[120px]" />
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <Skeleton className="h-4 w-[150px]" />
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <Skeleton className="h-4 w-[60px]" />
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <Skeleton className="h-4 w-[80px]" />
                </TableCell>
                <TableCell className="text-right">
                  <Skeleton className="h-4 w-[80px] ml-auto" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-[20px]" />
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  <Skeleton className="h-4 w-[60px]" />
                </TableCell>
                <TableCell>
                  <Skeleton className="h-4 w-[80px]" />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    );
  }

  if (!items || items.length === 0) {
    return (
      <div className="rounded-md border p-8 text-center text-muted-foreground">
        Brak pozycji w paragonie. Paragon może być w trakcie przetwarzania.
      </div>
    );
  }

  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Nazwa produktu</TableHead>
            <TableHead className="hidden md:table-cell">Kategoria</TableHead>
            <TableHead className="hidden md:table-cell">Tekst oryginalny</TableHead>
            <TableHead className="hidden md:table-cell">Ilość</TableHead>
            <TableHead className="hidden md:table-cell">Cena jednostkowa</TableHead>
            <TableHead className="text-right">Cena całkowita</TableHead>
            <TableHead>Pewność</TableHead>
            <TableHead className="hidden md:table-cell">Status</TableHead>
            <TableHead>Akcje</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.map((item) => {
            // Determine product name: use normalized name if available, otherwise original text
            const productName = item.index_name || item.original_text || '-';
            const isNormalized = !!item.index_name;
            const showOriginalTooltip = isNormalized && item.original_text;

            return (
              <TableRow key={item.id}>
                <TableCell>
                  {showOriginalTooltip ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <span className="font-medium">{productName}</span>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>Tekst oryginalny: {item.original_text}</p>
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    <span
                      className={cn(
                        isNormalized ? 'font-medium' : 'italic text-muted-foreground'
                      )}
                    >
                      {productName}
                    </span>
                  )}
                </TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground">
                  {item.category_name || '-'}
                </TableCell>
                <TableCell className="hidden md:table-cell text-muted-foreground">
                  {item.original_text || '-'}
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  {formatNumber(item.quantity)}
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  {formatPrice(item.unit_price)}
                </TableCell>
                <TableCell className="text-right font-medium">
                  {formatPrice(item.total_price)}
                </TableCell>
                <TableCell>
                  <ConfidenceIndicator score={item.confidence_score} />
                </TableCell>
                <TableCell className="hidden md:table-cell">
                  {item.is_verified ? (
                    <Tooltip>
                      <TooltipTrigger asChild>
                        <div className="flex items-center gap-1">
                          <Check className="h-4 w-4 text-green-600" />
                          <span className="text-sm text-muted-foreground">
                            {formatVerificationSource(item.verification_source)}
                          </span>
                        </div>
                      </TooltipTrigger>
                      <TooltipContent>
                        <p>
                          Zweryfikowane przez:{' '}
                          {formatVerificationSource(item.verification_source)}
                        </p>
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    <span className="text-sm text-muted-foreground">Niezweryfikowane</span>
                  )}
                </TableCell>
                <TableCell>
                  <div className="flex gap-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => onEdit?.(item)}
                    >
                      <Pencil className="h-3 w-3" />
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => onDelete?.(item)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
};

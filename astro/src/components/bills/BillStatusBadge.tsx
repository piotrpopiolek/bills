import React from 'react';
import { Badge } from '@/components/ui/badge';
import type { ProcessingStatus } from '@/types';

interface BillStatusBadgeProps {
  status: ProcessingStatus | null | undefined;
}

const statusConfig: Record<ProcessingStatus | string, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  pending: {
    label: 'Oczekujący',
    variant: 'secondary',
  },
  processing: {
    label: 'Przetwarzanie',
    variant: 'default',
  },
  to_verify: {
    label: 'Do weryfikacji',
    variant: 'outline',
  },
  completed: {
    label: 'Zakończony',
    variant: 'outline',
  },
  error: {
    label: 'Błąd',
    variant: 'destructive',
  },
};

export const BillStatusBadge: React.FC<BillStatusBadgeProps> = ({ status }) => {
  // Obsługa null/undefined
  if (!status) {
    return (
      <Badge variant="outline">
        Nieznany
      </Badge>
    );
  }
  
  const config = statusConfig[status];
  
  // Fallback dla nieznanych statusów
  if (!config) {
    console.warn(`Unknown status: ${status}`);
    return (
      <Badge variant="outline">
        {status}
      </Badge>
    );
  }

  const variant = config.variant || 'outline';
  const label = config.label || status;
  
  // For completed status, we need a custom green variant
  // Since Badge doesn't have a success variant by default, we'll use outline with custom styling
  if (status === 'completed') {
    return (
      <Badge variant="outline" className="border-green-500 text-green-700 dark:text-green-400">
        {label}
      </Badge>
    );
  }
  
  return (
    <Badge variant={variant as any}>
      {label}
    </Badge>
  );
};


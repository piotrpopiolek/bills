import type { APIRoute } from 'astro';
import { z } from 'zod';
import { proxyBackend } from '@/lib/server/backend-proxy';

export const prerender = false;

const IdSchema = z.coerce.number().int().positive();

const ItemPatchSchema = z
  .object({
    name: z.string().trim().min(1).max(255).optional(),
    quantity: z.coerce.number().positive().optional(),
    unit_price: z.coerce.number().min(0).optional(),
    total_price: z.coerce.number().min(0).optional(),
  })
  .refine(
    (value) =>
      value.name !== undefined ||
      value.quantity !== undefined ||
      value.unit_price !== undefined ||
      value.total_price !== undefined,
    { message: 'Brak zmian' },
  );

function badId(): Response {
  return new Response(JSON.stringify({ success: false, message: 'Nieprawidłowe ID' }), {
    status: 400,
    headers: { 'Content-Type': 'application/json' },
  });
}

export const PATCH: APIRoute = async ({ params, request, cookies }) => {
  const billId = IdSchema.safeParse(params.id);
  const itemId = IdSchema.safeParse(params.itemId);
  if (!billId.success || !itemId.success) {
    return badId();
  }
  const parsed = ItemPatchSchema.safeParse(await request.json().catch(() => null));
  if (!parsed.success) {
    return new Response(JSON.stringify({ success: false, message: 'Nieprawidłowe dane' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });
  }
  return proxyBackend(
    cookies,
    `/api/bills/${billId.data}/items/${itemId.data}`,
    'PATCH',
    parsed.data,
  );
};

export const DELETE: APIRoute = async ({ params, cookies }) => {
  const billId = IdSchema.safeParse(params.id);
  const itemId = IdSchema.safeParse(params.itemId);
  if (!billId.success || !itemId.success) {
    return badId();
  }
  return proxyBackend(
    cookies,
    `/api/bills/${billId.data}/items/${itemId.data}`,
    'DELETE',
  );
};

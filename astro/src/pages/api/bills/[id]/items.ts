import type { APIRoute } from 'astro';
import { z } from 'zod';
import type { BillItemListResponse, ApiResponse } from '@/types';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

// Zod schema for path parameter validation
const BillIdSchema = z.coerce.number().int().positive();

// Zod schema for query parameters validation
const BillItemsQuerySchema = z.object({
  skip: z.coerce.number().int().min(0).default(0),
  limit: z.coerce.number().int().min(1).max(100).default(100),
});

export const GET: APIRoute = async ({ params, url, cookies }) => {
  // Validate bill_id from path parameters
  const billIdParseResult = BillIdSchema.safeParse(params.id);

  if (!billIdParseResult.success) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Nieprawidłowe ID paragonu',
      }),
      {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }

  const billId = billIdParseResult.data;

  // Parse and validate query parameters
  const queryUrl = new URL(url);
  const queryParseResult = BillItemsQuerySchema.safeParse({
    skip: queryUrl.searchParams.get('skip') || '0',
    limit: queryUrl.searchParams.get('limit') || '100',
  });

  if (!queryParseResult.success) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Nieprawidłowe parametry zapytania',
      }),
      {
        status: 400,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }

  const { skip, limit } = queryParseResult.data;

  // Get access token from cookies
  const accessToken = cookies.get('access_token')?.value;

  if (!accessToken) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Brak autoryzacji',
      }),
      {
        status: 401,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }

  // Build query string
  const queryParams = new URLSearchParams();
  queryParams.append('skip', skip.toString());
  queryParams.append('limit', limit.toString());

  // Use environment variable for backend URL
  // Ensure HTTPS to prevent Mixed Content errors
  // Use process.env for SSR runtime (Railway compatibility)
  const BACKEND_URL = process.env.BACKEND_URL;
  if (!BACKEND_URL) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Backend URL not configured',
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
  
  // Ensure HTTPS for Railway public domains
  const secureBackendUrl = BACKEND_URL.startsWith('http://') 
    ? BACKEND_URL.replace('http://', 'https://')
    : BACKEND_URL;
  const API_URL = `${secureBackendUrl}/api/bills/${billId}/items`;

  console.log(`Proxying request to: ${API_URL}?${queryParams.toString()}`);

  try {
    const response = await fetch(`${API_URL}?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Upstream API error: ${response.status} ${errorText}`);

      let errorMessage = 'Wystąpił błąd podczas pobierania pozycji paragonu';
      if (response.status === 403) {
        errorMessage = 'Brak dostępu do tego paragonu';
      } else if (response.status === 404) {
        errorMessage = 'Paragon nie został znaleziony';
      } else if (response.status === 401) {
        errorMessage = 'Brak autoryzacji';
      }

      return new Response(
        JSON.stringify({
          success: false,
          message: errorMessage,
        }),
        {
          status: response.status,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
    }

    const data = (await response.json()) as BillItemListResponse;

    // Return wrapped response
    const apiResponse: ApiResponse<BillItemListResponse> = {
      success: true,
      data: data,
    };

    return new Response(JSON.stringify(apiResponse), {
      status: 200,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } catch (error) {
    console.error('Proxy error:', error);
    return new Response(
      JSON.stringify({
        success: false,
        message:
          error instanceof Error ? error.message : 'Unknown proxy error',
      }),
      {
        status: 500,
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );
  }
};


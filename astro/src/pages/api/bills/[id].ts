import type { APIRoute } from 'astro';
import { z } from 'zod';
import type { BillResponse, ApiResponse } from '@/types';
import { getBackendUrl } from '@/lib/utils/backend-url';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

// Zod schema for path parameter validation
const BillIdSchema = z.coerce.number().int().positive();

export const GET: APIRoute = async ({ params, cookies }) => {
  // Validate bill_id from path parameters
  const parseResult = BillIdSchema.safeParse(params.id);

  if (!parseResult.success) {
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

  const billId = parseResult.data;

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

  let secureBackendUrl: string;
  try {
    secureBackendUrl = getBackendUrl();
  } catch {
    console.error('BACKEND_URL is not set in environment variables');
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
  const API_URL = `${secureBackendUrl}/api/bills/${billId}`;

  console.log(`Proxying request to: ${API_URL}`);

  try {
    const response = await fetch(API_URL, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Upstream API error: ${response.status} ${errorText}`);

      let errorMessage = 'Wystąpił błąd podczas pobierania danych paragonu';
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

    const data = (await response.json()) as BillResponse;

    // Return wrapped response
    const apiResponse: ApiResponse<BillResponse> = {
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


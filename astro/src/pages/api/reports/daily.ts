import type { APIRoute } from 'astro';
import { z } from 'zod';
import type { DailyReportResponse, ApiResponse } from '@/types';
import { getBackendUrl } from '@/lib/utils/backend-url';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

// Zod schema for query parameters validation
const DailyReportQuerySchema = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Date must be in YYYY-MM-DD format').optional(),
});

export const GET: APIRoute = async ({ request, cookies }) => {
  const url = new URL(request.url);

  // Parse and validate query parameters using Zod
  const parseResult = DailyReportQuerySchema.safeParse({
    date: url.searchParams.get('date') || undefined,
  });

  // Early return for validation errors
  if (!parseResult.success) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Invalid query parameters',
        errors: parseResult.error.errors,
      }),
      {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  const { date } = parseResult.data;

  // Get access token from cookies or Authorization header
  const accessToken = cookies.get('access_token')?.value ||
    request.headers.get('Authorization')?.replace('Bearer ', '');

  if (!accessToken) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Unauthorized - missing access token',
      }),
      {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  const queryParams = new URLSearchParams();
  if (date) {
    queryParams.append('date', date);
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
  const API_URL = `${secureBackendUrl}/api/reports/daily`;

  console.log(`Proxying request to: ${API_URL}?${queryParams.toString()}`);

  try {
    const response = await fetch(`${API_URL}?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Upstream API error: ${response.status} ${errorText}`);
      return new Response(
        JSON.stringify({
          success: false,
          message: `Upstream API error: ${response.status}`,
        }),
        { status: response.status }
      );
    }

    const data = (await response.json()) as DailyReportResponse;

    // Return wrapped response
    const apiResponse: ApiResponse<DailyReportResponse> = {
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
        message: error instanceof Error ? error.message : 'Unknown proxy error',
      }),
      { status: 500 }
    );
  }
};

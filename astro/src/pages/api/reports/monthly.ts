import type { APIRoute } from 'astro';
import { z } from 'zod';
import type { MonthlyReportResponse, ApiResponse } from '@/types';
import { getBackendUrl } from '@/lib/utils/backend-url';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

// Zod schema for query parameters validation
const MonthlyReportQuerySchema = z.object({
  month: z.string().regex(/^\d{4}-\d{2}$/, 'Month must be in YYYY-MM format').optional(),
});

export const GET: APIRoute = async ({ request, cookies }) => {
  const url = new URL(request.url);

  // Parse and validate query parameters using Zod
  const parseResult = MonthlyReportQuerySchema.safeParse({
    month: url.searchParams.get('month') || undefined,
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

  const { month } = parseResult.data;

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
  if (month) {
    queryParams.append('month', month);
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
  const API_URL = `${secureBackendUrl}/api/reports/monthly`;

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

    const data = (await response.json()) as MonthlyReportResponse;
    
    // Log the response structure for debugging
    console.log('Monthly report response:', {
      hasTopCategories: !!data.top_categories,
      topCategoriesCount: data.top_categories?.length || 0,
      hasTopShops: !!data.top_shops,
      topShopsCount: data.top_shops?.length || 0,
      hasWeeklyBreakdown: !!data.weekly_breakdown,
      weeklyBreakdownCount: data.weekly_breakdown?.length || 0,
    });

    // Return wrapped response
    const apiResponse: ApiResponse<MonthlyReportResponse> = {
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

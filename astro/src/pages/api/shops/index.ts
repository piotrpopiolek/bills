import type { APIRoute } from 'astro';
import { z } from 'zod';
import type { ShopListResponse, ApiResponse } from '@/types';
import { getBackendUrl } from '@/lib/utils/backend-url';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

// Zod schema for query parameters validation
const ShopsQuerySchema = z.object({
  search: z.string().optional().default(''),
  skip: z.coerce.number().int().min(0).default(0),
  limit: z.coerce.number().int().min(1).max(100).default(10),
});

export const GET: APIRoute = async ({ request, cookies }) => {
  const url = new URL(request.url);
  
  // Parse and validate query parameters using Zod
  const parseResult = ShopsQuerySchema.safeParse({
    search: url.searchParams.get('search') || '',
    skip: url.searchParams.get('skip') || '0',
    limit: url.searchParams.get('limit') || '10',
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

  const { search, skip, limit } = parseResult.data;
  
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
  queryParams.append('skip', skip.toString());
  queryParams.append('limit', limit.toString());
  if (search) {
    queryParams.append('search', search);
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
  const API_URL = `${secureBackendUrl}/api/shops`;

  console.log(`Proxying request to: ${API_URL}?${queryParams.toString()}`);

  try {
    const response = await fetch(`${API_URL}?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`,
      }
    });

    if (!response.ok) {
        const errorText = await response.text();
        console.error(`Upstream API error: ${response.status} ${errorText}`);
        return new Response(JSON.stringify({
            success: false,
            message: `Upstream API error: ${response.status}`
        }), { status: response.status });
    }

    const data = await response.json() as ShopListResponse;
    
    // Return wrapped response
    const apiResponse: ApiResponse<ShopListResponse> = {
      success: true,
      data: data
    };

    return new Response(JSON.stringify(apiResponse), {
      status: 200,
      headers: {
        'Content-Type': 'application/json'
      }
    });

  } catch (error) {
    console.error('Proxy error:', error);
    return new Response(JSON.stringify({
      success: false,
      message: error instanceof Error ? error.message : 'Unknown proxy error'
    }), { status: 500 });
  }
};

import type { APIRoute } from 'astro';
import { z } from 'zod';
import type { CategoryListResponse, ApiResponse } from '@/types';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

// Zod schema for query parameters validation
const CategoriesQuerySchema = z.object({
  skip: z.coerce.number().int().min(0).default(0),
  limit: z.coerce.number().int().min(1).max(100).default(100),
});

export const GET: APIRoute = async ({ request, cookies }) => {
  const url = new URL(request.url);
  
  // Parse and validate query parameters using Zod
  const parseResult = CategoriesQuerySchema.safeParse({
    skip: url.searchParams.get('skip') || '0',
    limit: url.searchParams.get('limit') || '100',
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

  const { skip, limit } = parseResult.data;
  
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
  const API_URL = `${secureBackendUrl}/api/categories`;

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

    const data = await response.json() as CategoryListResponse;
    
    // Return wrapped response
    const apiResponse: ApiResponse<CategoryListResponse> = {
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

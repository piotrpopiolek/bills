import type { APIRoute } from 'astro';
import type { TokenResponse } from '@/lib/services/auth';
import { getBackendUrl } from '@/lib/utils/backend-url';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

export const GET: APIRoute = async ({ request }) => {
  const url = new URL(request.url);
  const token = url.searchParams.get('token');

  if (!token) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Missing token parameter',
      }),
      {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  let backendUrl: string;
  try {
    backendUrl = getBackendUrl();
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

  const API_URL = `${backendUrl}/api/auth/verify?token=${encodeURIComponent(token)}`;

  console.log(`Proxying request to: ${API_URL}`);

  try {
    const response = await fetch(API_URL, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Upstream API error: ${response.status} ${errorText}`);
      
      // Try to parse error as JSON
      let errorMessage = `Upstream API error: ${response.status}`;
      try {
        const errorJson = JSON.parse(errorText);
        errorMessage = errorJson.detail || errorJson.message || errorMessage;
      } catch {
        // If not JSON, use the text as is
        errorMessage = errorText || errorMessage;
      }
      
      return new Response(
        JSON.stringify({
          success: false,
          message: errorMessage,
        }),
        { 
          status: response.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Backend returns TokenResponse directly, no need to wrap
    const data = (await response.json()) as TokenResponse;

    return new Response(JSON.stringify(data), {
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
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
};


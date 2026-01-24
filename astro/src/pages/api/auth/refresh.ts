import type { APIRoute } from 'astro';
import type { TokenResponse } from '@/lib/services/auth';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

export const POST: APIRoute = async ({ request }) => {
  let body;
  try {
    body = await request.json();
  } catch (error) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Invalid JSON body',
      }),
      {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  const { refresh_token } = body;

  if (!refresh_token) {
    return new Response(
      JSON.stringify({
        success: false,
        message: 'Missing refresh_token in request body',
      }),
      {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }

  // Use environment variable for backend URL
  // Ensure HTTPS to prevent Mixed Content errors
  // Use process.env for SSR runtime (Railway compatibility)
  const BACKEND_URL = process.env.BACKEND_URL;
  
  if (!BACKEND_URL) {
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

  // Ensure HTTPS for Railway public domains
  const secureBackendUrl = BACKEND_URL.startsWith('http://') 
    ? BACKEND_URL.replace('http://', 'https://')
    : BACKEND_URL;
  const API_URL = `${secureBackendUrl}/api/auth/refresh`;

  console.log(`Proxying request to: ${API_URL}`);

  try {
    const response = await fetch(API_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token }),
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


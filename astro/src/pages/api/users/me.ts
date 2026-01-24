import type { APIRoute } from 'astro';
import type { UserProfile, ApiResponse } from '@/types';

// Mark this route as dynamic (not prerendered)
export const prerender = false;

export const GET: APIRoute = async ({ request, cookies }) => {
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
  const API_URL = `${secureBackendUrl}/api/users/me`;

  console.log(`Proxying request to: ${API_URL}`);

  try {
    const response = await fetch(API_URL, {
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

    const data = (await response.json()) as UserProfile;

    // Return wrapped response
    const apiResponse: ApiResponse<UserProfile> = {
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

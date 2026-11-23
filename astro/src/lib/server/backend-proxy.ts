import type { AstroCookies } from 'astro';
import { getBackendUrl } from '@/lib/utils/backend-url';

function json(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function messageFor(status: number): string {
  if (status === 401) {
    return 'Brak autoryzacji';
  }
  if (status === 403) {
    return 'Brak dostępu do tego paragonu';
  }
  if (status === 404) {
    return 'Nie znaleziono';
  }
  if (status === 422 || status === 400) {
    return 'Nieprawidłowe dane';
  }
  return 'Nie udało się zapisać zmian';
}

export async function proxyBackend(
  cookies: AstroCookies,
  path: string,
  method: string,
  body?: unknown,
): Promise<Response> {
  const accessToken = cookies.get('access_token')?.value;
  if (!accessToken) {
    return json({ success: false, message: 'Brak autoryzacji' }, 401);
  }

  let base: string;
  try {
    base = getBackendUrl();
  } catch {
    return json({ success: false, message: 'Backend URL not configured' }, 500);
  }

  try {
    const response = await fetch(`${base}${path}`, {
      method,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${accessToken}`,
      },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      return json({ success: false, message: messageFor(response.status) }, response.status);
    }
    if (response.status === 204) {
      return new Response(null, { status: 204 });
    }
    const data: unknown = await response.json();
    return json({ success: true, data }, response.status);
  } catch (error) {
    return json(
      {
        success: false,
        message: error instanceof Error ? error.message : 'Unknown proxy error',
      },
      500,
    );
  }
}

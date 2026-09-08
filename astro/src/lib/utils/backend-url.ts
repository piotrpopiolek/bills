/**
 * Resolve backend base URL for Astro SSR API proxies.
 * Prefer process.env (Railway), fall back to import.meta.env (astro dev).
 * Keep http for localhost; force https for public/production hosts.
 */
export function getBackendUrl(): string {
  const raw =
    process.env.BACKEND_URL ||
    (typeof import.meta !== 'undefined'
      ? (import.meta.env.BACKEND_URL as string | undefined)
      : undefined);

  if (!raw?.trim()) {
    throw new Error('BACKEND_URL is not set');
  }

  const backendUrl = raw.trim().replace(/\/$/, '');

  const isLocal =
    backendUrl.includes('localhost') || backendUrl.includes('127.0.0.1');

  if (isLocal) {
    return backendUrl;
  }

  if (backendUrl.startsWith('http://')) {
    return backendUrl.replace('http://', 'https://');
  }

  if (!backendUrl.startsWith('https://')) {
    return `https://${backendUrl}`;
  }

  return backendUrl;
}

/** @deprecated Prefer getBackendUrl() */
export function ensureHttpsBackendUrl(backendUrl: string | undefined): string {
  if (!backendUrl?.trim()) {
    throw new Error('BACKEND_URL is not set');
  }
  process.env.BACKEND_URL = backendUrl.trim();
  return getBackendUrl();
}

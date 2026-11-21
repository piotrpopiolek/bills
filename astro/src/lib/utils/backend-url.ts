/**
 * Resolve backend base URL for Astro SSR API proxies.
 * Prefer process.env, fall back to import.meta.env (astro dev).
 * Keep http for loopback and Docker-internal hosts; force https for public hosts.
 */
function isPrivateBackend(backendUrl: string): boolean {
  const withScheme = backendUrl.includes('://') ? backendUrl : `http://${backendUrl}`;

  let host: string;
  try {
    host = new URL(withScheme).hostname;
  } catch {
    return false;
  }

  if (
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host === '::1' ||
    host === 'host.docker.internal'
  ) {
    return true;
  }

  // Compose service names are a single DNS label, e.g. http://backend:8000.
  return !host.includes('.');
}

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

  if (isPrivateBackend(backendUrl)) {
    return backendUrl.startsWith('http://') || backendUrl.startsWith('https://')
      ? backendUrl
      : `http://${backendUrl}`;
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

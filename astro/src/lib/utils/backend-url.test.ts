import { afterEach, describe, expect, it } from 'vitest';

import { getBackendUrl } from './backend-url';

const ORIGINAL_BACKEND_URL = process.env.BACKEND_URL;

afterEach(() => {
  if (ORIGINAL_BACKEND_URL === undefined) {
    delete process.env.BACKEND_URL;
  } else {
    process.env.BACKEND_URL = ORIGINAL_BACKEND_URL;
  }
});

describe('getBackendUrl', () => {
  it('throws when the backend URL is missing', () => {
    delete process.env.BACKEND_URL;
    const meta = import.meta.env as { BACKEND_URL?: string };
    const previous = meta.BACKEND_URL;
    meta.BACKEND_URL = '';

    expect(() => getBackendUrl()).toThrow('BACKEND_URL is not set');

    meta.BACKEND_URL = previous;
  });

  it.each([
    {
      id: 'localhost-stays-http',
      raw: 'http://localhost:8000/',
      expected: 'http://localhost:8000',
    },
    {
      id: 'loopback-stays-http',
      raw: 'http://127.0.0.1:8000',
      expected: 'http://127.0.0.1:8000',
    },
    {
      id: 'public-http-becomes-https',
      raw: 'http://api.example.com',
      expected: 'https://api.example.com',
    },
    {
      id: 'bare-host-gets-https',
      raw: 'api.example.com',
      expected: 'https://api.example.com',
    },
    {
      id: 'https-is-unchanged',
      raw: 'https://api.example.com/',
      expected: 'https://api.example.com',
    },
  ])('$id', ({ raw, expected }) => {
    process.env.BACKEND_URL = raw;
    expect(getBackendUrl()).toBe(expected);
  });
});

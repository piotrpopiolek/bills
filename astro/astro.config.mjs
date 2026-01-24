// @ts-check
import { defineConfig } from 'astro/config';

import react from '@astrojs/react';
import node from '@astrojs/node';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  // SSR output for dynamic routes like /bills/[id]
  output: 'server',
  // Base path - empty for root domain, Railway handles routing
  base: '/',
  // Site URL - Railway will set this via environment variable
  // For production, this should be your Railway domain without port
  // Only set site if PUBLIC_SITE_URL is provided (Astro requires valid URL or undefined)
  ...(process.env.PUBLIC_SITE_URL && { site: process.env.PUBLIC_SITE_URL }),
  integrations: [react()],
  adapter: node({
    mode: 'standalone',
  }),

  vite: {
    plugins: [tailwindcss()]
  }
});
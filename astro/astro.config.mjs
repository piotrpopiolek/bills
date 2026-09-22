// @ts-check
import { defineConfig } from 'astro/config';

import react from '@astrojs/react';
import node from '@astrojs/node';
import tailwindcss from '@tailwindcss/vite';

// https://astro.build/config
export default defineConfig({
  // SSR output for dynamic routes like /bills/[id]
  output: 'server',
  base: '/',
  // PUBLIC_SITE_URL sets Astro.site when provided.
  ...(process.env.PUBLIC_SITE_URL && { site: process.env.PUBLIC_SITE_URL }),
  integrations: [react()],
  adapter: node({
    mode: 'standalone',
  }),

  vite: {
    plugins: [tailwindcss()]
  }
});
import { defineMiddleware } from 'astro:middleware';

export const onRequest = defineMiddleware((context, next) => {
  // Middleware is currently empty but can be used for:
  // - Request logging
  // - Setting custom headers
  // - Request/response transformation
  return next();
});

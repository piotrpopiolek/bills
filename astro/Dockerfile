# Build stage - Node.js environment for building Astro SSR application
FROM node:20-alpine AS builder

ARG NODE_ENV=production
WORKDIR /app

# Copy package files for dependency caching
COPY astro/package.json astro/package-lock.json ./

# Install dependencies (including devDependencies needed for build)
RUN npm ci --only=production=false && \
    npm cache clean --force

# Copy application source code
COPY astro/ .

# Build Astro application (SSR)
ARG PUBLIC_SITE_URL
ENV PUBLIC_SITE_URL=${PUBLIC_SITE_URL}
RUN npm run build

# Runtime stage - Node.js SSR server
FROM node:20-alpine AS runtime

ENV NODE_ENV=production
WORKDIR /app

# Install production dependencies
COPY astro/package.json astro/package-lock.json ./
RUN npm ci --omit=dev && \
    npm cache clean --force

# Copy built server output
COPY --from=builder /app/dist ./dist

# Expose port
EXPOSE 8080

# Runtime environment
ENV HOST=0.0.0.0
ENV PORT=8080
ENV BACKEND_URL=http://backend:8000

# Health check (uses built-in fetch in Node 20)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD node -e "fetch('http://localhost:' + (process.env.PORT || 8080) + '/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

# Run Astro SSR server
CMD ["node", "./dist/server/entry.mjs"]

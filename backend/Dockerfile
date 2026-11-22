FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

WORKDIR /app

# curl fetches the Supabase CLI. postgresql-client is a fallback for migrations.
RUN apt-get update && apt-get install -y \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Supabase CLI for running migrations
# Supabase CLI is required for `supabase db push` command
# Using binary installation from GitHub releases
RUN curl -fsSL https://github.com/supabase/cli/releases/latest/download/supabase_linux_amd64.tar.gz -o /tmp/supabase.tar.gz && \
    tar -xzf /tmp/supabase.tar.gz -C /tmp && \
    mv /tmp/supabase /usr/local/bin/supabase && \
    chmod +x /usr/local/bin/supabase && \
    rm /tmp/supabase.tar.gz && \
    supabase --version

# Build context is the repository root.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev
ENV PATH="/app/.venv/bin:$PATH"

# Copy backend application code
COPY backend/ .

# Copy supabase directory (migrations and config)
# This allows prestart.sh to access migrations and config
COPY supabase /supabase

# Copy and make prestart.sh executable
COPY backend/prestart.sh /prestart.sh
RUN sed -i 's/\r$//' /prestart.sh && chmod +x /prestart.sh

# Expose port 8000
EXPOSE 8000

# Create entrypoint script that runs migrations then starts the app.
# python:3.14-slim has /bin/sh, not bash.
RUN printf '%s\n' '#!/bin/sh' 'set -e' '/prestart.sh' 'exec uvicorn main:app --host 0.0.0.0 --port 8000' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]


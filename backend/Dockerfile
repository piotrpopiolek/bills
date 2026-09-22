FROM python:3.13-slim

# IMPORTANT: This Dockerfile expects build context to be the project root (/)
# In Railway, set Root Directory to / (root) and Build Command to:
# docker build -f backend/Dockerfile -t backend .
# Or let Railway auto-detect and use this Dockerfile from root

# Set working directory
WORKDIR /app

# Install system dependencies required for PaddleOCR and OpenCV
# Note: libgl1-mesa-glx is replaced by libgl1 in Debian 12+
# Also install postgresql-client for psql (fallback for migrations if Supabase CLI fails)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
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

# Copy requirements first for better layer caching
# Note: Build context should be project root, so we copy from backend/
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

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
# python:3.13-slim has /bin/sh, not bash.
RUN printf '%s\n' '#!/bin/sh' 'set -e' '/prestart.sh' 'exec uvicorn main:app --host 0.0.0.0 --port 8000' > /entrypoint.sh && \
    chmod +x /entrypoint.sh

# Use entrypoint script
ENTRYPOINT ["/entrypoint.sh"]


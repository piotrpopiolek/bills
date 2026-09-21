#!/bin/sh
set -e

echo "Checking database migrations..."

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set"
    exit 1
fi

# Check if migrations directory exists
MIGRATIONS_DIR="/supabase/migrations"
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "WARNING: Migrations directory not found at $MIGRATIONS_DIR"
    echo "Skipping migrations..."
    exit 0
fi

# Check if there are any migration files
MIGRATION_FILES=$(ls -1 "$MIGRATIONS_DIR"/*.sql 2>/dev/null | wc -l)
if [ "$MIGRATION_FILES" -eq 0 ]; then
    echo "WARNING: No migration files found in $MIGRATIONS_DIR"
    echo "Skipping migrations..."
    exit 0
fi

echo "Found $MIGRATION_FILES migration file(s)"
echo "Assuming migrations are already applied..."
echo "✓ Skipping migration process"
exit 0


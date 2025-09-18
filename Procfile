web: uvicorn main:app --host 0.0.0.0 --port $PORT
migrate: python scripts/railway_alembic.py upgrade head
migrate-status: python scripts/railway_alembic.py current

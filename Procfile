web: uvicorn main:app --host 0.0.0.0 --port $PORT
migrate: python scripts/alembic_wrapper.py upgrade head
migrate-rollback: python scripts/alembic_wrapper.py downgrade -1
migrate-status: python scripts/alembic_wrapper.py current
migrate-history: python scripts/alembic_wrapper.py history --verbose
web: python scripts/alembic_wrapper.py downgrade -1 && python scripts/alembic_wrapper.py upgrade head

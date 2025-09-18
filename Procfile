web: uvicorn main:app --host 0.0.0.0 --port $PORT
migrate: alembic upgrade head
migrate-rollback: alembic downgrade -1
migrate-status: alembic current
migrate-history: alembic history --verbose
migrate-rollback-remigrate: alembic downgrade -1 && alembic upgrade head

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check without database"""
    return {"status": "ok", "service": "bills-api"}


@router.get("/health/db")
async def health_check_db(db: AsyncSession = Depends(get_session)):
    """Health check with database connection test"""
    try:
        # Test database connection
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        # Test if tables exist (optional)
        result = await db.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
        table_count = result.scalar()

        return {"status": "ok", "database": "connected", "tables_count": table_count}
    except Exception as e:
        return {"status": "error", "database": "disconnected", "error": str(e)}

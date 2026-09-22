"""
HTTP routes for expense reports endpoints.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.main import get_session
from src.deps import CurrentUser
from src.reports.schemas import (
    DailyReportResponse,
    MonthlyReportResponse,
    WeeklyReportResponse,
)
from src.reports.services import ReportService

router = APIRouter()


def _get_current_week_start() -> date:
    """
    Calculate the start date of the current week (Monday).

    Returns:
        Date of the Monday of the current week
    """
    today = date.today()
    days_since_monday = today.weekday()
    return today - date.resolution * days_since_monday


def _get_current_month() -> str:
    """
    Get the current month in YYYY-MM format.

    Returns:
        Current month as string (e.g., "2024-01")
    """
    today = date.today()
    return today.strftime("%Y-%m")


async def get_report_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReportService:
    """
    Dependency to get ReportService instance.

    Args:
        session: Database session

    Returns:
        ReportService instance
    """
    return ReportService(session)


ServiceDependency = Annotated[ReportService, Depends(get_report_service)]


@router.get(
    "/daily",
    response_model=DailyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get daily expense report",
    description="Returns aggregated expense data for a specific day, including total amount, bills count, top 3 categories, and all shops with expenses.",
)
async def get_daily_report(
    user: CurrentUser,
    service: ServiceDependency,
    date_param: date | None = Query(
        None,
        alias="date",
        description="Date for the report (YYYY-MM-DD, default: today)",
    ),
) -> DailyReportResponse:
    """
    Get daily expense report.

    Args:
        user: Current authenticated user (from JWT token)
        service: ReportService instance
        date_param: Date for the report (default: today)

    Returns:
        DailyReportResponse with aggregated data for the day

    Raises:
        HTTPException 400: If date is invalid or in the future
        HTTPException 401: If user is not authenticated
    """
    report_date = date_param or date.today()
    return await service.get_daily_report(user.id, report_date)


@router.get(
    "/weekly",
    response_model=WeeklyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get weekly expense report",
    description="Returns aggregated expense data for a specific week, including total amount, bills count, daily breakdown, and top 3 categories.",
)
async def get_weekly_report(
    user: CurrentUser,
    service: ServiceDependency,
    week_start: date | None = Query(
        None,
        description="Start date of the week (YYYY-MM-DD, Monday, default: current week start)",
    ),
) -> WeeklyReportResponse:
    """
    Get weekly expense report.

    Args:
        user: Current authenticated user (from JWT token)
        service: ReportService instance
        week_start: Start date of the week (Monday, default: current week start)

    Returns:
        WeeklyReportResponse with aggregated data for the week

    Raises:
        HTTPException 400: If week_start is invalid or in the future
        HTTPException 401: If user is not authenticated
    """
    week_start_date = week_start or _get_current_week_start()
    return await service.get_weekly_report(user.id, week_start_date)


@router.get(
    "/monthly",
    response_model=MonthlyReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get monthly expense report",
    description="Returns aggregated expense data for a specific month, including total amount, bills count, daily average, top 3 categories, top 3 shops, and weekly breakdown.",
)
async def get_monthly_report(
    user: CurrentUser,
    service: ServiceDependency,
    month: str | None = Query(
        None, description="Month for the report (YYYY-MM, default: current month)"
    ),
) -> MonthlyReportResponse:
    """
    Get monthly expense report.

    Args:
        user: Current authenticated user (from JWT token)
        service: ReportService instance
        month: Month for the report (YYYY-MM, default: current month)

    Returns:
        MonthlyReportResponse with aggregated data for the month

    Raises:
        HTTPException 400: If month format is invalid or month is in the future
        HTTPException 401: If user is not authenticated
    """
    month_str = month or _get_current_month()
    return await service.get_monthly_report(user.id, month_str)

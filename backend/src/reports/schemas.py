"""
Pydantic schemas for expense reports.

All schemas use strict=True (via AppBaseModel) to prevent implicit type coercion.
"""

import re
from datetime import date as date_type
from decimal import Decimal

from pydantic import Field, field_validator

from src.common.schemas import AppBaseModel


# --- Helper Info Schemas ---
class CategoryInfo(AppBaseModel):
    """Category information for reports."""

    id: int = Field(..., gt=0, description="Category ID")
    name: str = Field(..., min_length=1, description="Category name")


class ShopInfo(AppBaseModel):
    """Shop information for reports."""

    id: int = Field(..., gt=0, description="Shop ID")
    name: str = Field(..., min_length=1, description="Shop name")


# --- Summary Schemas ---
class CategorySummary(AppBaseModel):
    """Category summary with amount and percentage."""

    category: CategoryInfo = Field(..., description="Category information")
    amount: Decimal = Field(
        ..., ge=0, description="Total amount spent in this category"
    )
    percentage: Decimal = Field(
        ..., ge=0, le=100, description="Percentage of total amount"
    )


class ShopSummary(AppBaseModel):
    """Shop summary with amount and bills count."""

    shop: ShopInfo = Field(..., description="Shop information")
    amount: Decimal = Field(..., ge=0, description="Total amount spent at this shop")
    bills_count: int = Field(..., ge=0, description="Number of bills from this shop")


# --- Breakdown Schemas ---
class DailyBreakdown(AppBaseModel):
    """Daily breakdown for weekly reports."""

    date: date_type = Field(..., description="Date")
    amount: Decimal = Field(..., ge=0, description="Total amount for this day")
    bills_count: int = Field(..., ge=0, description="Number of bills for this day")


class WeeklyBreakdown(AppBaseModel):
    """Weekly breakdown for monthly reports."""

    week_start: date_type = Field(..., description="Start date of the week (Monday)")
    amount: Decimal = Field(..., ge=0, description="Total amount for this week")


# --- Report Response Schemas ---
class DailyReportResponse(AppBaseModel):
    """Response schema for daily expense report."""

    date: date_type = Field(..., description="Report date")
    total_amount: Decimal = Field(
        ..., ge=0, description="Total amount spent on this day"
    )
    bills_count: int = Field(..., ge=0, description="Number of bills on this day")
    top_categories: list[CategorySummary] = Field(
        ..., max_length=10, description="Top 10 categories by amount spent"
    )
    shops: list[ShopSummary] = Field(
        ..., description="All shops with expenses on this day"
    )


class WeeklyReportResponse(AppBaseModel):
    """Response schema for weekly expense report."""

    week_start: date_type = Field(..., description="Start date of the week (Monday)")
    week_end: date_type = Field(..., description="End date of the week (Sunday)")
    total_amount: Decimal = Field(
        ..., ge=0, description="Total amount spent in this week"
    )
    bills_count: int = Field(
        ..., ge=0, description="Total number of bills in this week"
    )
    daily_breakdown: list[DailyBreakdown] = Field(
        ..., max_length=7, description="Daily breakdown for all 7 days of the week"
    )
    top_categories: list[CategorySummary] = Field(
        ..., max_length=10, description="Top 10 categories by amount spent in this week"
    )


class MonthlyReportResponse(AppBaseModel):
    """Response schema for monthly expense report."""

    month: str = Field(..., description="Month in format YYYY-MM")
    total_amount: Decimal = Field(
        ..., ge=0, description="Total amount spent in this month"
    )
    bills_count: int = Field(
        ..., ge=0, description="Total number of bills in this month"
    )
    daily_average: Decimal = Field(..., ge=0, description="Average daily amount spent")
    top_categories: list[CategorySummary] = Field(
        ...,
        max_length=10,
        description="Top 10 categories by amount spent in this month",
    )
    top_shops: list[ShopSummary] = Field(
        ..., max_length=10, description="Top 10 shops by amount spent in this month"
    )
    weekly_breakdown: list[WeeklyBreakdown] = Field(
        ..., description="Weekly breakdown for all weeks in this month"
    )


# --- Query Parameter Schemas ---
class ReportsQueryParams(AppBaseModel):
    """
    Query parameters for reports endpoints.

    Note: Each endpoint uses only one of these fields (date, week_start, or month).
    """

    date: date_type | None = Field(
        None, description="Date for daily report (YYYY-MM-DD, default: today)"
    )
    week_start: date_type | None = Field(
        None,
        description="Week start date for weekly report (YYYY-MM-DD, Monday, default: current week start)",
    )
    month: str | None = Field(
        None, description="Month for monthly report (YYYY-MM, default: current month)"
    )

    @field_validator("date", "week_start")
    @classmethod
    def validate_date_not_future(cls, v: date_type | None, info) -> date_type | None:
        """Validate that date is not in the future."""
        if v is not None:
            today = date_type.today()
            if v > today:
                raise ValueError("Data nie może być w przyszłości")
        return v

    @field_validator("month")
    @classmethod
    def validate_month_format(cls, v: str | None) -> str | None:
        """Validate month format (YYYY-MM)."""
        if v is not None:
            if not re.match(r"^\d{4}-\d{2}$", v):
                raise ValueError(
                    "Nieprawidłowy format miesiąca. Oczekiwany format: YYYY-MM"
                )
            # Validate month range (01-12)
            try:
                year, month = map(int, v.split("-"))
                if month < 1 or month > 12:
                    raise ValueError("Miesiąc musi być w zakresie 01-12")
            except ValueError as e:
                raise ValueError(
                    "Nieprawidłowy format miesiąca. Oczekiwany format: YYYY-MM"
                ) from e
        return v

"""
Report service for generating expense reports.

This service provides methods to generate daily, weekly, and monthly expense reports
with aggregated data from bills and bill_items.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.bill_items.models import BillItem
from src.bills.models import Bill, ProcessingStatus
from src.categories.models import Category
from src.reports.exceptions import InvalidDateRangeError, InvalidMonthFormatError
from src.reports.schemas import (
    CategoryInfo,
    CategorySummary,
    DailyBreakdown,
    DailyReportResponse,
    MonthlyReportResponse,
    ShopInfo,
    ShopSummary,
    WeeklyBreakdown,
    WeeklyReportResponse,
)
from src.shops.models import Shop

logger = logging.getLogger(__name__)


class ReportService:
    """
    Service for generating expense reports.

    This service does not inherit from AppService because it doesn't manage
    individual entities, but rather aggregates data across multiple entities.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_daily_report(
        self, user_id: int, report_date: date
    ) -> DailyReportResponse:
        """
        Generate daily expense report for a specific date.

        Args:
            user_id: ID of the user requesting the report
            report_date: Date for the report (default: today)

        Returns:
            DailyReportResponse with aggregated data for the day

        Raises:
            InvalidDateRangeError: If date is in the future
        """
        # Validate date is not in the future
        today = date.today()
        if report_date > today:
            raise InvalidDateRangeError("Data nie może być w przyszłości")

        logger.info(f"Generating daily report for user {user_id}, date: {report_date}")

        # Calculate date range (start and end of day)
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = datetime.combine(report_date, datetime.max.time())

        # Query 1: Get total amount and bills count for the day
        total_stmt = (
            select(
                func.coalesce(func.sum(BillItem.total_price), Decimal("0.00")).label(
                    "total_amount"
                ),
                func.count(func.distinct(Bill.id)).label("bills_count"),
            )
            .select_from(Bill)
            .outerjoin(BillItem, Bill.id == BillItem.bill_id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    Bill.bill_date >= start_datetime,
                    Bill.bill_date <= end_datetime,
                    Bill.status == ProcessingStatus.COMPLETED,
                )
            )
        )
        total_result = await self.session.execute(total_stmt)
        total_row = total_result.one()
        total_amount = total_row.total_amount or Decimal("0.00")
        bills_count = total_row.bills_count or 0

        # Query 2: Get top 10 categories
        categories_stmt = (
            select(
                Category.id,
                Category.name,
                func.sum(BillItem.total_price).label("amount"),
            )
            .select_from(BillItem)
            .join(Bill, BillItem.bill_id == Bill.id)
            .outerjoin(Category, BillItem.category_id == Category.id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    func.date(Bill.bill_date) == report_date,
                    Bill.status == ProcessingStatus.COMPLETED,
                    BillItem.category_id.isnot(None),
                )
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(BillItem.total_price).desc())
            .limit(10)
        )
        categories_result = await self.session.execute(categories_stmt)
        categories_rows = categories_result.all()

        # Build top categories with percentages
        top_categories: list[CategorySummary] = []
        for row in categories_rows:
            category_amount = row.amount or Decimal("0.00")
            percentage = (
                self._calculate_percentage(category_amount, total_amount)
                if total_amount > 0
                else Decimal("0.00")
            )

            top_categories.append(
                CategorySummary(
                    category=CategoryInfo(id=row.id, name=row.name),
                    amount=category_amount,
                    percentage=percentage,
                )
            )

        # Query 3: Get all shops with expenses
        shops_stmt = (
            select(
                Shop.id,
                Shop.name,
                func.sum(BillItem.total_price).label("amount"),
                func.count(func.distinct(Bill.id)).label("bills_count"),
            )
            .select_from(Bill)
            .join(BillItem, Bill.id == BillItem.bill_id)
            .outerjoin(Shop, Bill.shop_id == Shop.id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    func.date(Bill.bill_date) == report_date,
                    Bill.status == ProcessingStatus.COMPLETED,
                    Bill.shop_id.isnot(None),
                )
            )
            .group_by(Shop.id, Shop.name)
            .order_by(func.sum(BillItem.total_price).desc())
        )
        shops_result = await self.session.execute(shops_stmt)
        shops_rows = shops_result.all()

        # Build shops list
        shops: list[ShopSummary] = []
        for row in shops_rows:
            shops.append(
                ShopSummary(
                    shop=ShopInfo(id=row.id, name=row.name),
                    amount=row.amount or Decimal("0.00"),
                    bills_count=row.bills_count or 0,
                )
            )

        return DailyReportResponse(
            date=report_date,
            total_amount=total_amount,
            bills_count=bills_count,
            top_categories=top_categories,
            shops=shops,
        )

    async def get_weekly_report(
        self, user_id: int, week_start: date
    ) -> WeeklyReportResponse:
        """
        Generate weekly expense report for a specific week.

        Args:
            user_id: ID of the user requesting the report
            week_start: Start date of the week (Monday)

        Returns:
            WeeklyReportResponse with aggregated data for the week

        Raises:
            InvalidDateRangeError: If week_start is in the future
        """
        # Validate date is not in the future
        today = date.today()
        if week_start > today:
            raise InvalidDateRangeError("Data nie może być w przyszłości")

        logger.info(
            f"Generating weekly report for user {user_id}, week_start: {week_start}"
        )

        # Calculate week range (Monday to Sunday)
        week_end = week_start + timedelta(days=6)

        # Query 1: Get daily breakdown for the week
        daily_stmt = (
            select(
                func.date(Bill.bill_date).label("date"),
                func.coalesce(func.sum(BillItem.total_price), Decimal("0.00")).label(
                    "amount"
                ),
                func.count(func.distinct(Bill.id)).label("bills_count"),
            )
            .select_from(Bill)
            .outerjoin(BillItem, Bill.id == BillItem.bill_id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    func.date(Bill.bill_date) >= week_start,
                    func.date(Bill.bill_date) <= week_end,
                    Bill.status == ProcessingStatus.COMPLETED,
                )
            )
            .group_by(func.date(Bill.bill_date))
            .order_by(func.date(Bill.bill_date))
        )
        daily_result = await self.session.execute(daily_stmt)
        daily_rows = daily_result.all()

        # Build daily breakdown (ensure all 7 days are present)
        daily_breakdown: list[DailyBreakdown] = []
        current_date = week_start
        daily_dict = {row.date: row for row in daily_rows}

        for _ in range(7):
            if current_date in daily_dict:
                row = daily_dict[current_date]
                daily_breakdown.append(
                    DailyBreakdown(
                        date=current_date,
                        amount=row.amount or Decimal("0.00"),
                        bills_count=row.bills_count or 0,
                    )
                )
            else:
                daily_breakdown.append(
                    DailyBreakdown(
                        date=current_date, amount=Decimal("0.00"), bills_count=0
                    )
                )
            current_date += timedelta(days=1)

        # Query 2: Get total amount and bills count for the week
        total_stmt = (
            select(
                func.coalesce(func.sum(BillItem.total_price), Decimal("0.00")).label(
                    "total_amount"
                ),
                func.count(func.distinct(Bill.id)).label("bills_count"),
            )
            .select_from(Bill)
            .outerjoin(BillItem, Bill.id == BillItem.bill_id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    func.date(Bill.bill_date) >= week_start,
                    func.date(Bill.bill_date) <= week_end,
                    Bill.status == ProcessingStatus.COMPLETED,
                )
            )
        )
        total_result = await self.session.execute(total_stmt)
        total_row = total_result.one()
        total_amount = total_row.total_amount or Decimal("0.00")
        bills_count = total_row.bills_count or 0

        # Query 3: Get top 10 categories for the week
        categories_stmt = (
            select(
                Category.id,
                Category.name,
                func.sum(BillItem.total_price).label("amount"),
            )
            .select_from(BillItem)
            .join(Bill, BillItem.bill_id == Bill.id)
            .outerjoin(Category, BillItem.category_id == Category.id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    func.date(Bill.bill_date) >= week_start,
                    func.date(Bill.bill_date) <= week_end,
                    Bill.status == ProcessingStatus.COMPLETED,
                    BillItem.category_id.isnot(None),
                )
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(BillItem.total_price).desc())
            .limit(10)
        )
        categories_result = await self.session.execute(categories_stmt)
        categories_rows = categories_result.all()

        # Build top categories with percentages
        top_categories: list[CategorySummary] = []
        for row in categories_rows:
            category_amount = row.amount or Decimal("0.00")
            percentage = (
                self._calculate_percentage(category_amount, total_amount)
                if total_amount > 0
                else Decimal("0.00")
            )

            top_categories.append(
                CategorySummary(
                    category=CategoryInfo(id=row.id, name=row.name),
                    amount=category_amount,
                    percentage=percentage,
                )
            )

        return WeeklyReportResponse(
            week_start=week_start,
            week_end=week_end,
            total_amount=total_amount,
            bills_count=bills_count,
            daily_breakdown=daily_breakdown,
            top_categories=top_categories,
        )

    async def get_monthly_report(
        self, user_id: int, month: str
    ) -> MonthlyReportResponse:
        """
        Generate monthly expense report for a specific month.

        Args:
            user_id: ID of the user requesting the report
            month: Month in format YYYY-MM

        Returns:
            MonthlyReportResponse with aggregated data for the month

        Raises:
            InvalidMonthFormatError: If month format is invalid
            InvalidDateRangeError: If month is in the future
        """
        # Parse and validate month
        try:
            year, month_num = map(int, month.split("-"))
            if month_num < 1 or month_num > 12:
                raise InvalidMonthFormatError("Miesiąc musi być w zakresie 01-12")
            month_start = date(year, month_num, 1)
        except (ValueError, TypeError) as e:
            raise InvalidMonthFormatError(
                "Nieprawidłowy format miesiąca. Oczekiwany format: YYYY-MM"
            ) from e

        # Calculate month end (last day of month)
        if month_num == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month_num + 1, 1) - timedelta(days=1)

        # Validate month is not in the future
        today = date.today()
        if month_start > today:
            raise InvalidDateRangeError("Miesiąc nie może być w przyszłości")

        logger.info(f"Generating monthly report for user {user_id}, month: {month}")

        start_datetime = datetime.combine(month_start, datetime.min.time())

        # Query 1: Get total amount and bills count for the month
        total_stmt = (
            select(
                func.coalesce(func.sum(BillItem.total_price), Decimal("0.00")).label(
                    "total_amount"
                ),
                func.count(func.distinct(Bill.id)).label("bills_count"),
            )
            .select_from(Bill)
            .outerjoin(BillItem, Bill.id == BillItem.bill_id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    func.date_trunc("month", Bill.bill_date)
                    == func.date_trunc("month", start_datetime),
                    Bill.status == ProcessingStatus.COMPLETED,
                )
            )
        )
        total_result = await self.session.execute(total_stmt)
        total_row = total_result.one()
        total_amount = total_row.total_amount or Decimal("0.00")
        bills_count = total_row.bills_count or 0

        # Calculate daily average
        days_in_month = (month_end - month_start).days + 1
        daily_average = (
            total_amount / Decimal(str(days_in_month))
            if days_in_month > 0
            else Decimal("0.00")
        )

        # Query 2: Get top 10 categories for the month
        categories_stmt = (
            select(
                Category.id,
                Category.name,
                func.sum(BillItem.total_price).label("amount"),
            )
            .select_from(BillItem)
            .join(Bill, BillItem.bill_id == Bill.id)
            .outerjoin(Category, BillItem.category_id == Category.id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    func.date_trunc("month", Bill.bill_date)
                    == func.date_trunc("month", start_datetime),
                    Bill.status == ProcessingStatus.COMPLETED,
                    BillItem.category_id.isnot(None),
                )
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(BillItem.total_price).desc())
            .limit(10)
        )
        categories_result = await self.session.execute(categories_stmt)
        categories_rows = categories_result.all()

        # Build top categories with percentages
        top_categories: list[CategorySummary] = []
        for row in categories_rows:
            category_amount = row.amount or Decimal("0.00")
            percentage = (
                self._calculate_percentage(category_amount, total_amount)
                if total_amount > 0
                else Decimal("0.00")
            )

            top_categories.append(
                CategorySummary(
                    category=CategoryInfo(id=row.id, name=row.name),
                    amount=category_amount,
                    percentage=percentage,
                )
            )

        # Query 3: Get top 10 shops for the month
        shops_stmt = (
            select(
                Shop.id,
                Shop.name,
                func.sum(BillItem.total_price).label("amount"),
                func.count(func.distinct(Bill.id)).label("bills_count"),
            )
            .select_from(Bill)
            .join(BillItem, Bill.id == BillItem.bill_id)
            .outerjoin(Shop, Bill.shop_id == Shop.id)
            .where(
                and_(
                    Bill.user_id == user_id,
                    func.date_trunc("month", Bill.bill_date)
                    == func.date_trunc("month", start_datetime),
                    Bill.status == ProcessingStatus.COMPLETED,
                    Bill.shop_id.isnot(None),
                )
            )
            .group_by(Shop.id, Shop.name)
            .order_by(func.sum(BillItem.total_price).desc())
            .limit(10)
        )
        shops_result = await self.session.execute(shops_stmt)
        shops_rows = shops_result.all()

        # Build top shops
        top_shops: list[ShopSummary] = []
        for row in shops_rows:
            top_shops.append(
                ShopSummary(
                    shop=ShopInfo(id=row.id, name=row.name),
                    amount=row.amount or Decimal("0.00"),
                    bills_count=row.bills_count or 0,
                )
            )

        # Query 4: Get weekly breakdown for the month
        # Calculate all week starts in the month
        weekly_breakdown: list[WeeklyBreakdown] = []
        current_week_start = month_start
        # Find the Monday of the week containing month_start
        days_since_monday = current_week_start.weekday()
        if days_since_monday > 0:
            current_week_start = current_week_start - timedelta(days=days_since_monday)

        while current_week_start <= month_end:
            week_end_date = current_week_start + timedelta(days=6)

            # Query for this week
            week_stmt = (
                select(
                    func.coalesce(
                        func.sum(BillItem.total_price), Decimal("0.00")
                    ).label("amount")
                )
                .select_from(Bill)
                .outerjoin(BillItem, Bill.id == BillItem.bill_id)
                .where(
                    and_(
                        Bill.user_id == user_id,
                        func.date(Bill.bill_date) >= current_week_start,
                        func.date(Bill.bill_date) <= week_end_date,
                        Bill.status == ProcessingStatus.COMPLETED,
                    )
                )
            )
            week_result = await self.session.execute(week_stmt)
            week_amount = week_result.scalar_one_or_none() or Decimal("0.00")

            weekly_breakdown.append(
                WeeklyBreakdown(week_start=current_week_start, amount=week_amount)
            )

            current_week_start += timedelta(days=7)

        return MonthlyReportResponse(
            month=month,
            total_amount=total_amount,
            bills_count=bills_count,
            daily_average=daily_average,
            top_categories=top_categories,
            top_shops=top_shops,
            weekly_breakdown=weekly_breakdown,
        )

    def _calculate_percentage(self, amount: Decimal, total: Decimal) -> Decimal:
        """
        Calculate percentage of amount relative to total.

        Args:
            amount: Partial amount
            total: Total amount

        Returns:
            Percentage as Decimal (0-100)
        """
        if total == 0:
            return Decimal("0.00")
        return (amount / total * Decimal("100.00")).quantize(Decimal("0.01"))

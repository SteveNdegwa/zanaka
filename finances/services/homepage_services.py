# dashboard/views.py or services/homepage_services.py
from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta, datetime
from decimal import Decimal

from finances.models import (
    Payment, PaymentStatus, Expense, ExpenseStatus,
    Refund, RefundStatus, Invoice
)
from schools.models import Branch, Classroom
from users.models import User, RoleName


class HomepageServices:
    @classmethod
    def get_homepage_statistics(
            cls,
            user: User,
            branch_id: Optional[str] = None,
            period: Optional[str] = None,
            start_date: Optional[str] = None,
            end_date: Optional[str] = None
    ):
        school = user.school

        print(branch_id, period, start_date, end_date)

        # Determine date range
        if start_date and end_date:
            try:
                start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
                if start_date > end_date:
                    raise ValidationError('Start date cannot be after end date')
                custom_range = (start_date, end_date)
                period_label = f"{start_date} to {end_date}"
            except ValueError:
                raise ValidationError('Invalid date format (YYYY-MM-DD)')
        elif period and period != "all":
            predefined = cls._get_current_period_range(period)
            if not predefined:
                raise ValidationError('Invalid period value')
            custom_range = predefined
            period_label = period.replace("_", " ").title()
        else:
            custom_range = None
            period_label = "All Time"

        # School-wide base stats (independent of period)
        total_branches = Branch.objects.filter(school=school, is_active=True).count()
        total_classrooms = Classroom.objects.filter(branch__school=school, is_active=True).count()

        # Active students (school-wide)
        students_qs = User.objects.filter(role__name=RoleName.STUDENT, is_active=True, school=school)

        # Cash flow querysets
        payments_qs = Payment.objects.filter(
            Q(status=PaymentStatus.COMPLETED) |
            Q(status=PaymentStatus.PARTIALLY_REFUNDED) |
            Q(status=PaymentStatus.REFUNDED),
            student__school=school
        )

        expenses_qs = Expense.objects.filter(status=ExpenseStatus.PAID, school=school)

        refunds_qs = Refund.objects.filter(
            status=RefundStatus.COMPLETED,
            original_payment__student__school=school
        )

        # Apply branch filter
        if branch_id:
            try:
                branch = Branch.objects.get(id=branch_id)
                students_qs = students_qs.filter(branches=branch)
                payments_qs = payments_qs.filter(student__branches=branch)
                expenses_qs = expenses_qs.filter(
                    Q(branches=branch) | Q(branches__isnull=True, school=branch.school)
                )
                refunds_qs = refunds_qs.filter(original_payment__student__branches=branch)

                # Branch-specific school stats
                total_branches = 1
                total_classrooms = Classroom.objects.filter(branch=branch, is_active=True).count()
            except Branch.DoesNotExist:
                raise ValidationError('Branch not found')

        # Apply date filtering for cash flow
        if custom_range:
            start_date, end_date = custom_range
            payments_qs = payments_qs.filter(created_at__date__gte=start_date, created_at__date__lte=end_date)
            expenses_qs = expenses_qs.filter(expense_date__gte=start_date, expense_date__lte=end_date)
            refunds_qs = refunds_qs.filter(processed_at__date__gte=start_date, processed_at__date__lte=end_date)

        # Cash-based Revenue Calculation
        gross_cash_received = payments_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        cash_refunded = refunds_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_cash_revenue = gross_cash_received - cash_refunded

        expenses_amount = expenses_qs.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        net_cash_profit = net_cash_revenue - expenses_amount

        # Other operational metrics
        active_students = students_qs.count()

        # Outstanding & Overdue (accrual view, school-wide)
        outstanding_balance = Decimal('0.00')
        overdue_balance = Decimal('0.00')
        for inv in Invoice.objects.filter(student__school=school):
            if inv.balance > 0:
                outstanding_balance += inv.balance
                if inv.due_date < timezone.now().date():
                    overdue_balance += inv.balance

        pending_payments = Payment.objects.filter(status=PaymentStatus.PENDING).count()

        new_admissions = 0
        if custom_range:
            new_admissions = students_qs.filter(
                created_at__date__gte=start_date,
                created_at__date__lte=end_date
            ).count()

        # Previous period comparison
        revenue_change = {"change": None, "message": "N/A", "is_positive": None}
        profit_change = {"change": None, "message": "N/A", "is_positive": None}
        if custom_range and period != "all":
            prev_start, prev_end = cls._get_previous_period_range(*custom_range)

            prev_gross_cash = Payment.objects.filter(
                Q(status=PaymentStatus.COMPLETED) |
                Q(status=PaymentStatus.PARTIALLY_REFUNDED) |
                Q(status=PaymentStatus.REFUNDED),
                created_at__date__gte=prev_start,
                created_at__date__lte=prev_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            prev_refunds = Refund.objects.filter(
                status=RefundStatus.COMPLETED,
                processed_at__date__gte=prev_start,
                processed_at__date__lte=prev_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            prev_net_cash = prev_gross_cash - prev_refunds
            revenue_change = cls._calculate_percentage_change(net_cash_revenue, prev_net_cash)

            prev_expenses = Expense.objects.filter(
                status=ExpenseStatus.PAID,
                expense_date__gte=prev_start,
                expense_date__lte=prev_end
            ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

            prev_profit = prev_net_cash - prev_expenses
            profit_change = cls._calculate_percentage_change(net_cash_profit, prev_profit)

        return {
            "school_stats": {
                "total_branches": total_branches,
                "total_classrooms": total_classrooms,
                "active_students": active_students,
                "new_admissions": new_admissions,
            },
            "gross_cash_received": {
                "amount": float(gross_cash_received),
                "formatted": f"KSh {gross_cash_received:,.2f}",
            },
            "refunds_issued": {
                "amount": float(cash_refunded),
                "formatted": f"KSh {cash_refunded:,.2f}",
            },
            "net_cash_revenue": {
                "amount": float(net_cash_revenue),
                "formatted": f"KSh {net_cash_revenue:,.2f}",
                "change": revenue_change["change"],
                "message": revenue_change["message"],
                "is_positive": revenue_change["is_positive"],
            },
            "expenses": {
                "amount": float(expenses_amount),
                "formatted": f"KSh {expenses_amount:,.2f}",
            },
            "net_cash_profit": {
                "amount": float(net_cash_profit),
                "formatted": f"KSh {net_cash_profit:,.2f}",
                "change": profit_change["change"],
                "message": profit_change["message"],
                "is_positive": profit_change["is_positive"],
            },
            "outstanding_balance": {
                "amount": float(outstanding_balance),
                "formatted": f"KSh {outstanding_balance:,.2f}",
            },
            "overdue_balance": {
                "amount": float(overdue_balance),
                "formatted": f"KSh {overdue_balance:,.2f}",
            },
            "pending_payments": pending_payments,
            "period": {
                "label": period_label,
                "start": custom_range[0].isoformat() if custom_range else None,
                "end": custom_range[1].isoformat() if custom_range else None,
            },
        }

    @classmethod
    def _get_current_period_range(cls, period: str):
        now = timezone.now().date()
        ranges = {
            'today': (now, now),
            'yesterday': (now - timedelta(days=1), now - timedelta(days=1)),
            'this_week': (now - timedelta(days=now.weekday()), now),
            'last_week': (
                now - timedelta(days=now.weekday() + 7),
                now - timedelta(days=now.weekday() + 1),
            ),
            'this_month': (now.replace(day=1), now),
            'last_month': (
                (now.replace(day=1) - timedelta(days=1)).replace(day=1),
                now.replace(day=1) - timedelta(days=1),
            ),
            'this_year': (now.replace(month=1, day=1), now),
            'last_year': (
                now.replace(year=now.year - 1, month=1, day=1),
                now.replace(year=now.year - 1, month=12, day=31),
            ),
        }
        return ranges.get(period)

    @classmethod
    def _get_previous_period_range(cls, current_start, current_end):
        duration = current_end - current_start
        return current_start - duration - timedelta(days=1), current_end - duration - timedelta(days=1)

    @classmethod
    def _calculate_percentage_change(cls, current: Decimal, previous: Decimal) -> dict:
        if previous == 0:
            return {'change': None, 'message': 'N/A (no previous data)', 'is_positive': None}
        change = ((current - previous) / previous) * 100
        return {
            'change': round(change, 1),
            'message': f'{'Up' if change > 0 else 'Down'} {abs(round(change, 1))}% vs previous period',
            'is_positive': change > 0,
        }
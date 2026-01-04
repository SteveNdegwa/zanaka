from typing import Optional
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone

from base.services.base_services import BaseServices
from finances.models import (
    Expense, ExpenseCategory, Vendor, Department, ExpenseAttachment,
    PettyCash, PettyCashTransaction, ExpenseStatus,
    ExpensePaymentMethod, PettyCashStatus, School, Branch
)
from users.models import User


class ExpenseServices(BaseServices):
    """
    Service layer for managing expenses.
    """

    fk_mappings = {
        'category_id': ('finances.ExpenseCategory', 'category'),
        'department_id': ('finances.Department', 'department'),
        'vendor_id': ('finances.Vendor', 'vendor'),
        'school_id': ('schools.School', 'school'),
        'requested_by_id': ('users.User', 'requested_by'),
        'approved_by_id': ('users.User', 'approved_by'),
        'rejected_by_id': ('users.User', 'rejected_by'),
        'paid_by_id': ('users.User', 'paid_by'),
    }

    @classmethod
    def get_expense(
            cls,
            expense_id: str,
            status: Optional[str] = None,
            select_for_update: bool = False
    ) -> Expense:
        filters = Q(id=expense_id)
        if status:
            filters &= Q(status=status.upper())

        qs = Expense.objects
        if select_for_update:
            qs = qs.select_for_update()

        return qs.get(filters)

    @classmethod
    @transaction.atomic
    def create_expense(cls, user: User, **data) -> Expense:
        required_fields = {
            'name', 'category_id', 'department_id', 'amount', 'expense_date'
        }
        field_types = {
            'amount': float,
            'tax_rate': float,
            'is_taxable': bool,
            'is_recurring': bool
        }
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        expense = Expense.objects.create(
            name=data['name'],
            school=user.school,
            category=data['category'],
            department=data['department'],
            vendor=data.get('vendor'),
            amount=Decimal(str(data['amount'])),
            expense_date=data.get('expense_date'),
            status=ExpenseStatus.DRAFT,
            invoice_number=data.get('invoice_number', ""),
            requested_by=user,
            is_taxable=data.get('is_taxable', False),
            tax_rate=Decimal(str(data.get('tax_rate', 0))),
            is_recurring=data.get('is_recurring', False),
            recurrence_frequency=data.get('recurrence_frequency'),
            notes=data.get('notes', "")
        )

        # Handle branches
        branch_ids = data.get('branch_ids', [])
        if branch_ids:
            branches = Branch.objects.filter(id__in=branch_ids, is_active=True)
            expense.branches.set(branches)

        return expense

    @classmethod
    @transaction.atomic
    def update_expense(cls, user: User, expense_id: str, **data) -> Expense:
        expense = cls.get_expense(expense_id, select_for_update=True)

        if not expense.can_edit(user):
            raise ValidationError('You do not have permission to edit this expense')

        field_types = {
            'amount': float,
            'tax_rate': float,
            'is_taxable': bool,
            'is_recurring': bool
        }
        data = cls._sanitize_and_validate_data(data, field_types=field_types)

        update_fields = ['updated_by']

        if 'name' in data:
            expense.name = data['name']
            update_fields.append('name')

        if 'school_id' in data:
            expense.school = School.objects.get(id=data['school_id'])
            update_fields.append('school')

        if 'category_id' in data:
            expense.category = ExpenseCategory.objects.get(id=data['category_id'], is_active=True)
            update_fields.append('category')

        if 'department_id' in data:
            expense.department = Department.objects.get(id=data['department_id'], is_active=True)
            update_fields.append('department')

        if 'vendor_id' in data:
            expense.vendor = Vendor.objects.get(id=data['vendor_id'], is_active=True) if data['vendor_id'] else None
            update_fields.append('vendor')

        if 'amount' in data:
            expense.amount = Decimal(str(data['amount']))
            update_fields.append('amount')

        if 'expense_date' in data:
            expense.expense_date = data['expense_date']
            update_fields.append('expense_date')

        if 'invoice_number' in data:
            expense.invoice_number = data['invoice_number']
            update_fields.append('invoice_number')

        if 'receipt_number' in data:
            expense.receipt_number = data['receipt_number']
            update_fields.append('receipt_number')

        if 'cheque_number' in data:
            expense.cheque_number = data['cheque_number']
            update_fields.append('cheque_number')

        if 'transaction_reference' in data:
            expense.transaction_reference = data['transaction_reference']
            update_fields.append('transaction_reference')

        if 'is_taxable' in data:
            expense.is_taxable = data['is_taxable']
            update_fields.append('is_taxable')

        if 'tax_rate' in data:
            expense.tax_rate = Decimal(str(data['tax_rate']))
            update_fields.append('tax_rate')

        if 'is_recurring' in data:
            expense.is_recurring = data['is_recurring']
            update_fields.append('is_recurring')

        if 'recurrence_frequency' in data:
            expense.recurrence_frequency = data['recurrence_frequency']
            update_fields.append('recurrence_frequency')

        if 'notes' in data:
            expense.notes = data['notes']
            update_fields.append('notes')

        # Handle branches update
        if 'branch_ids' in data:
            branch_ids = data['branch_ids']
            if branch_ids:
                branches = Branch.objects.filter(id__in=branch_ids, is_active=True)
                expense.branches.set(branches)
            else:
                expense.branches.clear()

        expense.updated_by = user
        expense.save(update_fields=update_fields)

        return expense

    @classmethod
    @transaction.atomic
    def submit_for_approval(cls, user: User, expense_id: str) -> Expense:
        expense = cls.get_expense(expense_id, select_for_update=True)

        if expense.status != ExpenseStatus.DRAFT:
            raise ValidationError('Only draft expenses can be submitted for approval')

        if expense.requested_by != user:
            raise ValidationError('Only the requester can submit this expense')

        if expense.category.requires_approval:
            expense.status = ExpenseStatus.PENDING_APPROVAL
        else:
            expense.status = ExpenseStatus.APPROVED
            expense.approved_by = user
            expense.approved_at = timezone.now()

        expense.updated_by = user
        expense.save(update_fields=['status', 'approved_by', 'approved_at'])

        return expense

    @classmethod
    @transaction.atomic
    def approve_expense(cls, user: User, expense_id: str) -> Expense:
        expense = cls.get_expense(expense_id, select_for_update=True)

        if expense.status != ExpenseStatus.PENDING_APPROVAL:
            raise ValidationError('Only pending expenses can be approved')

        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = user
        expense.approved_at = timezone.now()
        expense.save(update_fields=['status', 'approved_by', 'approved_at'])

        return expense

    @classmethod
    @transaction.atomic
    def reject_expense(cls, user: User, expense_id: str, rejection_reason: str) -> Expense:
        expense = cls.get_expense(expense_id, select_for_update=True)

        if expense.status != ExpenseStatus.PENDING_APPROVAL:
            raise ValidationError('Only pending expenses can be rejected')

        if not rejection_reason:
            raise ValidationError('Rejection reason is required')

        expense.status = ExpenseStatus.REJECTED
        expense.rejected_by = user
        expense.rejected_at = timezone.now()
        expense.rejection_reason = rejection_reason
        expense.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason'])

        return expense

    @classmethod
    @transaction.atomic
    def mark_as_paid(cls, user: User, expense_id: str, **payment_data) -> Expense:
        expense = cls.get_expense(expense_id, select_for_update=True)

        payment_method = payment_data.pop('payment_method')
        if not payment_method:
            raise ValidationError('Payment method is required')

        if payment_method == ExpensePaymentMethod.MPESA:
            if not payment_data.get('receipt_number'):
                raise ValidationError('Mpesa receipt number is required for Mpesa payments')

        if expense.status != ExpenseStatus.APPROVED:
            raise ValidationError('Only approved expenses can be marked as paid')

        # Handle petty cash
        if payment_method == ExpensePaymentMethod.PETTY_CASH:
            petty_cash_fund_id = payment_data.get('petty_cash_fund_id')
            if not petty_cash_fund_id:
                raise ValidationError('Petty cash fund is required')

            petty_cash_found = PettyCash.objects.select_for_update().get(
                id=petty_cash_fund_id,
                status=PettyCashStatus.ACTIVE
            )

            if petty_cash_found.status != PettyCashStatus.ACTIVE:
                raise ValidationError(f'Petty cash fund is {petty_cash_found.status.lower()}')

            if petty_cash_found.current_balance < expense.total_amount:
                raise ValidationError(
                    f'Insufficient balance. Available: {petty_cash_found.current_balance}, '
                    f'Required: {expense.total_amount}'
                )

            petty_cash_found.disburse(
                expense=expense,
                disbursed_by=user,
                notes=payment_data.get('notes', '')
            )

        expense.status = ExpenseStatus.PAID
        expense.payment_method = payment_method
        expense.paid_by = user
        expense.paid_at = timezone.now()

        update_fields = ['status', 'payment_method', 'paid_by', 'paid_at']

        optional_fields = [
            'receipt_number', 'cheque_number', 'transaction_reference'
        ]
        for field in optional_fields:
            if payment_data.get(field):
                setattr(expense, field, payment_data[field])
                update_fields.append(field)

        expense.save(update_fields=update_fields)

        return expense

    @classmethod
    @transaction.atomic
    def cancel_expense(cls, user: User, expense_id: str) -> Expense:
        expense = cls.get_expense(expense_id, select_for_update=True)

        if expense.status in [ExpenseStatus.PAID, ExpenseStatus.CANCELLED]:
            raise ValidationError('Paid or cancelled expenses cannot be cancelled')

        expense.status = ExpenseStatus.CANCELLED
        expense.save(update_fields=['status'])

        return expense

    @classmethod
    def fetch_expense(cls, expense_id: str) -> dict:
        expense = cls.get_expense(expense_id)

        branches = [
            {"id": str(b.id), "name": b.name}
            for b in expense.branches.filter(is_active=True)
        ]

        attachments = list(
            ExpenseAttachment.objects
            .filter(expense=expense, is_active=True)
            .values(
                'id', 'file', 'file_name', 'file_type', 'file_size',
                'uploaded_by_id', 'created_at'
            )
        )

        return {
            'id': str(expense.id),
            'expense_reference': expense.expense_reference,
            'name': expense.name,
            'school_id': str(expense.school.id),
            'school_name': expense.school.name,
            'branches': branches,
            'category_id': str(expense.category.id),
            'category_name': expense.category.name,
            'department_id': str(expense.department.id),
            'department_name': expense.department.name,
            'vendor_id': str(expense.vendor.id) if expense.vendor else None,
            'vendor_name': expense.vendor.name if expense.vendor else None,
            'amount': str(expense.amount),
            'tax_amount': str(expense.tax_amount),
            'total_amount': str(expense.total_amount),
            'expense_date': expense.expense_date.isoformat() if expense.expense_date else None,
            'payment_method': expense.payment_method,
            'status': expense.status,
            'invoice_number': expense.invoice_number,
            'receipt_number': expense.receipt_number,
            'cheque_number': expense.cheque_number,
            'transaction_reference': expense.transaction_reference,
            'requested_by_id': str(expense.requested_by.id),
            'requested_by_full_name': expense.requested_by.full_name,
            'approved_by_id': str(expense.approved_by.id) if expense.approved_by else None,
            'approved_by_full_name': expense.approved_by.full_name if expense.approved_by else None,
            'approved_at': expense.approved_at.isoformat() if expense.approved_at else None,
            'rejected_by_id': str(expense.rejected_by.id) if expense.rejected_by else None,
            'rejected_by_full_name': expense.rejected_by.full_name if expense.rejected_by else None,
            'rejected_at': expense.rejected_at.isoformat() if expense.rejected_at else None,
            'rejection_reason': expense.rejection_reason,
            'paid_by_id': str(expense.paid_by.id) if expense.paid_by else None,
            'paid_by_full_name': expense.paid_by.full_name if expense.paid_by else None,
            'paid_at': expense.paid_at.isoformat() if expense.paid_at else None,
            'is_taxable': expense.is_taxable,
            'tax_rate': str(expense.tax_rate),
            'is_recurring': expense.is_recurring,
            'recurrence_frequency': expense.recurrence_frequency,
            'notes': expense.notes,
            'created_at': expense.created_at.isoformat(),
            'updated_at': expense.updated_at.isoformat(),
            'attachments': attachments
        }

    @classmethod
    def filter_expenses(cls, **filters) -> list[dict]:
        field_types = {'amount': float}
        filters = cls._sanitize_and_validate_data(filters, field_types=field_types)

        qs = Expense.objects.all()

        # Foreign key filters
        if filters.get('school_id'):
            qs = qs.filter(school_id=filters['school_id'])
        if filters.get('vendor_id'):
            qs = qs.filter(vendor_id=filters['vendor_id'])
        if filters.get('department_id'):
            qs = qs.filter(department_id=filters['department_id'])
        if filters.get('category_id'):
            qs = qs.filter(category_id=filters['category_id'])

        # Status filter
        if filters.get('status'):
            qs = qs.filter(status=filters['status'].upper())

        # Date range
        if filters.get('start_date'):
            qs = qs.filter(expense_date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(expense_date__lte=filters['end_date'])

        # Amount range
        if filters.get('min_amount'):
            qs = qs.filter(amount__gte=Decimal(str(filters['min_amount'])))
        if filters.get('max_amount'):
            qs = qs.filter(amount__lte=Decimal(str(filters['max_amount'])))

        # Search term
        search_term = filters.get('search_term')
        if search_term:
            search_q = Q()
            fields = [
                'expense_reference', 'name', 'invoice_number', 'receipt_number',
                'category__name', 'department__name', 'vendor__name'
            ]
            for field in fields:
                search_q |= Q(**{f'{field}__icontains': search_term})
            qs = qs.filter(search_q)

        qs = qs.order_by('-created_at')
        expense_ids = qs.values_list('id', flat=True)
        return [cls.fetch_expense(expense_id) for expense_id in expense_ids]

    @classmethod
    def get_expense_summary(cls, **filters) -> dict:
        qs = Expense.objects.all()

        if filters.get('start_date'):
            qs = qs.filter(expense_date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(expense_date__lte=filters['end_date'])
        if filters.get('school_id'):
            qs = qs.filter(school_id=filters['school_id'])
        if filters.get('department_id'):
            qs = qs.filter(department_id=filters['department_id'])
        if filters.get('category_id'):
            qs = qs.filter(category_id=filters['category_id'])
        if filters.get('status'):
            qs = qs.filter(status=filters['status'].upper())

        summary = qs.aggregate(
            total_expenses=Sum('amount'),
            total_count=Count('id')
        )

        status_breakdown = qs.values('status').annotate(
            count=Count('id'),
            total=Sum('amount')
        )

        return {
            'total_amount': str(summary['total_expenses'] or Decimal('0.00')),
            'total_count': summary['total_count'] or 0,
            'status_breakdown': [
                {
                    'status': item['status'],
                    'count': item['count'],
                    'total': str(item['total'] or Decimal('0.00'))
                }
                for item in status_breakdown
            ]
        }

    @classmethod
    @transaction.atomic
    def add_attachment(cls, user: User, expense_id: str, file) -> ExpenseAttachment:
        expense = cls.get_expense(expense_id)
        attachment = ExpenseAttachment.objects.create(
            expense=expense,
            file=file,
            uploaded_by=user
        )
        return attachment

    @classmethod
    @transaction.atomic
    def remove_attachment(cls, user: User, attachment_id: str) -> None:
        attachment = ExpenseAttachment.objects.get(id=attachment_id, is_active=True)
        attachment.is_active = False
        attachment.save(update_fields=['is_active'])
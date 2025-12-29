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
    ExpensePaymentMethod, PettyCashStatus
)
from users.models import User


class ExpenseServices(BaseServices):
    """
    Service layer for managing expenses, including creation, update, approval,
    rejection, payment, cancellation, and filtering.
    """

    fk_mappings = {
        'category_id': ('finances.ExpenseCategory', 'category'),
        'department_id': ('finances.Department', 'department'),
        'vendor_id': ('finances.Vendor', 'vendor'),
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
        """
        Retrieve a single expense by ID, optionally filtering by status and/or
        locking for update.

        :param expense_id: ID of the expense to retrieve.
        :type expense_id: str
        :param status: Optional status filter.
        :type status: str | None
        :param select_for_update: If True, lock the row for update.
        :type select_for_update: bool
        :raises Expense.DoesNotExist: If the expense does not exist.
        :return: Expense instance.
        :rtype: Expense
        """
        filters = Q(id=expense_id)
        if status:
            filters &= Q(status=status.lower())

        qs = Expense.objects
        if select_for_update:
            qs = qs.select_for_update()

        return qs.get(filters)

    @classmethod
    @transaction.atomic
    def create_expense(cls, user: User, **data) -> Expense:
        """
        Create a new expense.

        :param user: User creating the expense.
        :type user: User
        :param data: Expense data including 'category_id', 'department_id', 'amount', etc.
        :type data: dict
        :raises ValidationError: If required fields are missing or invalid.
        :return: Created expense instance.
        :rtype: Expense
        """
        required_fields = {'name', 'category_id', 'department_id', 'amount', 'expense_date'}
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

        category = ExpenseCategory.objects.get(id=data['category_id'], is_active=True)
        department = Department.objects.get(id=data['department_id'], is_active=True)

        vendor = None
        if data.get('vendor_id'):
            vendor = Vendor.objects.get(id=data['vendor_id'], is_active=True)

        # Always create as draft - user can review before submitting
        expense = Expense.objects.create(
            name=data['name'],
            category=category,
            department=department,
            vendor=vendor,
            amount=Decimal(str(data['amount'])),
            expense_date=data.get('expense_date'),
            status=ExpenseStatus.DRAFT,
            invoice_number=data.get('invoice_number', """),
            requested_by=user,
            is_taxable=data.get('is_taxable', False),
            tax_rate=Decimal(str(data.get('tax_rate', 0))),
            is_recurring=data.get('is_recurring', False),
            recurrence_frequency=data.get('recurrence_frequency'),
            notes=data.get('notes', """)
        )

        return expense

    @classmethod
    @transaction.atomic
    def update_expense(cls, user: User, expense_id: str, **data) -> Expense:
        """
        Update an existing expense.

        :param user: User performing the update.
        :type user: User
        :param expense_id: ID of the expense to update.
        :type expense_id: str
        :param data: Updated expense data.
        :type data: dict
        :raises ValidationError: If expense cannot be edited or fields are invalid.
        :return: Updated expense instance.
        :rtype: Expense
        """
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

        expense.updated_by = user
        expense.save(update_fields=update_fields)

        return expense

    @classmethod
    @transaction.atomic
    def submit_for_approval(cls, user: User, expense_id: str) -> Expense:
        """
        Submit an expense for approval. If category doesn't require approval,
        auto-approve immediately.

        :param user: User submitting the expense.
        :type user: User
        :param expense_id: ID of the expense to submit.
        :type expense_id: str
        :raises ValidationError: If expense is not in draft status.
        :return: Updated expense instance.
        :rtype: Expense
        """
        expense = cls.get_expense(expense_id, select_for_update=True)

        if expense.status != ExpenseStatus.DRAFT:
            raise ValidationError('Only draft expenses can be submitted for approval')

        if expense.requested_by != user:
            raise ValidationError('Only the requester can submit this expense')

        # Check if category requires approval
        if expense.category.requires_approval:
            # Needs approval - set to pending
            expense.status = ExpenseStatus.PENDING_APPROVAL
            expense.updated_by = user
            expense.save(update_fields=['status', 'updated_by'])
        else:
            # No approval needed - auto-approve
            expense.status = ExpenseStatus.APPROVED
            expense.approved_by = user
            expense.approved_at = timezone.now()
            expense.updated_by = user
            expense.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_by'])

        return expense

    @classmethod
    @transaction.atomic
    def approve_expense(cls, user: User, expense_id: str) -> Expense:
        """
        Approve a pending expense.

        :param user: User approving the expense.
        :type user: User
        :param expense_id: ID of the expense to approve.
        :type expense_id: str
        :raises ValidationError: If user cannot approve or expense is not pending.
        :return: Approved expense instance.
        :rtype: Expense
        """
        expense = cls.get_expense(expense_id, select_for_update=True)

        if not expense.status == ExpenseStatus.PENDING_APPROVAL:
            raise ValidationError('Only pending expenses can be approved')

        expense.status = ExpenseStatus.APPROVED
        expense.approved_by = user
        expense.approved_at = timezone.now()
        expense.updated_by = user
        expense.save(update_fields=['status', 'approved_by', 'approved_at', 'updated_by'])

        return expense

    @classmethod
    @transaction.atomic
    def reject_expense(cls, user: User, expense_id: str, rejection_reason: str) -> Expense:
        """
        Reject a pending expense.

        :param user: User rejecting the expense.
        :type user: User
        :param expense_id: ID of the expense to reject.
        :type expense_id: str
        :param rejection_reason: Reason for rejection.
        :type rejection_reason: str
        :raises ValidationError: If user cannot reject or expense is not pending.
        :return: Rejected expense instance.
        :rtype: Expense
        """
        expense = cls.get_expense(expense_id, select_for_update=True)

        if expense.status != ExpenseStatus.PENDING_APPROVAL:
            raise ValidationError('Only pending expenses can be rejected')

        if not rejection_reason:
            raise ValidationError('Rejection reason is required')

        expense.status = ExpenseStatus.REJECTED
        expense.rejected_by = user
        expense.rejected_at = timezone.now()
        expense.rejection_reason = rejection_reason
        expense.updated_by = user
        expense.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason', 'updated_by'])

        return expense

    @classmethod
    @transaction.atomic
    def mark_as_paid(cls, user: User, expense_id: str, payment_method: str, **payment_data) -> Expense:
        """
        Mark an approved expense as paid.

        :param user: User marking the expense as paid.
        :type user: User
        :param expense_id: ID of the expense to mark as paid.
        :type expense_id: str
        :param payment_method: Payment method used (bank_transfer, cheque, cash, mpesa, petty_cash).
        :type payment_method: str
        :param payment_data: Optional payment details like transaction_reference, petty_cash_fund_id.
        :type payment_data: dict
        :raises ValidationError: If expense is not approved or petty cash fund insufficient.
        :return: Paid expense instance.
        :rtype: Expense
        """
        expense = cls.get_expense(expense_id, select_for_update=True)

        if expense.status != ExpenseStatus.APPROVED:
            raise ValidationError('Only approved expenses can be marked as paid')

        if not payment_method:
            raise ValidationError('Payment method is required')

        # Handle petty cash payment
        if payment_method == ExpensePaymentMethod.PETTY_CASH:
            petty_cash_fund_id = payment_data.get('petty_cash_fund_id')
            if not petty_cash_fund_id:
                raise ValidationError('Petty cash fund is required for petty cash payments')

            petty_cash_fund = PettyCash.objects.select_for_update().get(
                id=petty_cash_fund_id,
                status=PettyCashStatus.ACTIVE
            )

            # Check if sufficient balance
            if petty_cash_fund.current_balance < expense.total_amount:
                raise ValidationError(
                    f'Insufficient petty cash balance. Available: {petty_cash_fund.current_balance}, '
                    f'Required: {expense.total_amount}'
                )

            # Create petty cash transaction
            PettyCashTransaction.objects.create(
                petty_cash_fund=petty_cash_fund,
                description=f'Payment for {expense.expense_reference} - {expense.name}',
                transaction_type='disbursement',
                amount=expense.total_amount,
                expense=expense,
                processed_by=user,
                notes=payment_data.get('notes', '')
            )

        expense.status = ExpenseStatus.PAID
        expense.payment_method = payment_method
        expense.paid_by = user
        expense.paid_at = timezone.now()
        expense.updated_by = user

        update_fields = ['status', 'payment_method', 'paid_by', 'paid_at', 'updated_by']

        if payment_data.get('receipt_number'):
            expense.receipt_number = payment_data['receipt_number']
            update_fields.append('receipt_number')

        if payment_data.get('cheque_number'):
            expense.cheque_number = payment_data['cheque_number']
            update_fields.append('cheque_number')

        if payment_data.get('transaction_reference'):
            expense.transaction_reference = payment_data['transaction_reference']
            update_fields.append('transaction_reference')

        expense.save(update_fields=update_fields)

        return expense

    @classmethod
    @transaction.atomic
    def cancel_expense(cls, user: User, expense_id: str) -> Expense:
        """
        Cancel an expense.

        :param user: User cancelling the expense.
        :type user: User
        :param expense_id: ID of the expense to cancel.
        :type expense_id: str
        :raises ValidationError: If expense is already paid or cancelled.
        :return: Cancelled expense instance.
        :rtype: Expense
        """
        expense = cls.get_expense(expense_id, select_for_update=True)

        if expense.status in [ExpenseStatus.PAID, ExpenseStatus.CANCELLED]:
            raise ValidationError('Paid or cancelled expenses cannot be cancelled')

        expense.status = ExpenseStatus.CANCELLED
        expense.updated_by = user
        expense.save(update_fields=['status', 'updated_by'])

        return expense

    @classmethod
    def fetch_expense(cls, expense_id: str) -> dict:
        """
        Retrieve expense details along with attachments.

        :param expense_id: ID of the expense to fetch.
        :type expense_id: str
        :return: Dictionary with expense and attachment details.
        :rtype: dict
        """
        expense = cls.get_expense(expense_id)

        attachments = list(
            ExpenseAttachment.objects
            .filter(expense=expense, is_active=True)
            .values(
                'id', 'file', 'file_name', 'file_type', 'file_size',
                'uploaded_by_id', 'uploaded_at'
            )
        )

        return {
            'id': str(expense.id),
            'expense_reference': expense.expense_reference,
            'name': expense.name,
            'category_id': str(expense.category.id),
            'category_name': expense.category.name,
            'category_full_path': expense.category.get_full_path(),
            'department_id': str(expense.department.id),
            'department_name': expense.department.name,
            'vendor_id': str(expense.vendor.id) if expense.vendor else None,
            'vendor_name': expense.vendor.name if expense.vendor else None,
            'amount': expense.amount,
            'tax_amount': expense.tax_amount,
            'total_amount': expense.total_amount,
            'expense_date': expense.expense_date,
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
            'approved_at': expense.approved_at,
            'rejected_by_id': str(expense.rejected_by.id) if expense.rejected_by else None,
            'rejected_by_full_name': expense.rejected_by.full_name if expense.rejected_by else None,
            'rejected_at': expense.rejected_at,
            'rejection_reason': expense.rejection_reason,
            'paid_by_id': str(expense.paid_by.id) if expense.paid_by else None,
            'paid_by_full_name': expense.paid_by.full_name if expense.paid_by else None,
            'paid_at': expense.paid_at,
            'is_taxable': expense.is_taxable,
            'tax_rate': expense.tax_rate,
            'is_recurring': expense.is_recurring,
            'recurrence_frequency': expense.recurrence_frequency,
            'notes': expense.notes,
            'created_at': expense.created_at,
            'updated_at': expense.updated_at,
            'attachments': attachments
        }

    @classmethod
    def filter_expenses(cls, **filters) -> list[dict]:
        """
        Filter expenses based on fields and a search term.

        :param filters: Keyword arguments containing expense fields and optional 'search_term'.
        :type filters: dict
        :return: List of expense dictionaries matching filters.
        :rtype: list[dict]
        """
        field_types = {'amount': float}
        filters = cls._sanitize_and_validate_data(filters, field_types=field_types)

        expense_field_names = {f.name for f in Expense._meta.get_fields()}
        cleaned_filters = {k: v for k, v in filters.items() if k in expense_field_names}

        qs = Expense.objects.filter(**cleaned_filters).order_by('-created_at')

        # Date range filters
        if filters.get('start_date'):
            qs = qs.filter(expense_date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(expense_date__lte=filters['end_date'])

        # Amount range filters
        if filters.get('min_amount'):
            qs = qs.filter(amount__gte=Decimal(str(filters['min_amount'])))
        if filters.get('max_amount'):
            qs = qs.filter(amount__lte=Decimal(str(filters['max_amount'])))

        search_term = filters.get('search_term')
        if search_term:
            fields = [
                'expense_reference',
                'name',
                'category__name',
                'department__name',
                'vendor__name',
                'invoice_number',
                'receipt_number',
                'status',
            ]
            search_q = Q()

            for field in fields:
                search_q |= Q(**{f'{field}__icontains': search_term})

            qs = qs.filter(search_q)

        expense_ids = qs.values_list('id', flat=True)
        return [cls.fetch_expense(expense_id) for expense_id in expense_ids]

    @classmethod
    @transaction.atomic
    def add_attachment(cls, user: User, expense_id: str, file) -> ExpenseAttachment:
        """
        Add an attachment to an expense.

        :param user: User uploading the attachment.
        :type user: User
        :param expense_id: ID of the expense.
        :type expense_id: str
        :param file: File to attach.
        :return: Created attachment instance.
        :rtype: ExpenseAttachment
        """
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
        """
        Remove an attachment from an expense.

        :param user: User removing the attachment.
        :type user: User
        :param attachment_id: ID of the attachment to remove.
        :type attachment_id: str
        """
        attachment = ExpenseAttachment.objects.get(id=attachment_id, is_active=True)
        attachment.is_active = False
        attachment.save(update_fields=['is_active'])

    @classmethod
    def get_expense_summary(cls, **filters) -> dict:
        """
        Get summary statistics for expenses.

        :param filters: Filter criteria including date ranges, department, category, status.
        :type filters: dict
        :return: Dictionary with summary statistics.
        :rtype: dict
        """
        qs = Expense.objects.all()

        if filters.get('start_date'):
            qs = qs.filter(expense_date__gte=filters['start_date'])
        if filters.get('end_date'):
            qs = qs.filter(expense_date__lte=filters['end_date'])
        if filters.get('department_id'):
            qs = qs.filter(department_id=filters['department_id'])
        if filters.get('category_id'):
            qs = qs.filter(category_id=filters['category_id'])
        if filters.get('status'):
            qs = qs.filter(status=filters['status'])

        summary = qs.aggregate(
            total_expenses=Sum('amount'),
            total_count=Count('id')
        )

        status_breakdown = qs.values('status').annotate(
            count=Count('id'),
            total=Sum('amount')
        )

        return {
            'total_amount': summary['total_expenses'] or Decimal('0.00'),
            'total_count': summary['total_count'] or 0,
            'status_breakdown': list(status_breakdown)
        }

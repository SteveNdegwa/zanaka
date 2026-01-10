import logging

from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, F
from django.utils import timezone

from base.services.base_services import BaseServices
from finances.models import Invoice, FeeItem, GradeLevelFee, InvoiceItem, PaymentAllocation, InvoiceStatus, BulkInvoice
from notifications.models import NotificationType
from notifications.services.notification_services import NotificationServices
from users.models import User, RoleName
from users.services.user_services import UserServices

logger = logging.getLogger(__name__)


class InvoiceServices(BaseServices):
    """
    Service layer for managing invoices, including creation, update, cancellation,
    activation, fetching, and filtering.
    """

    fk_mappings = {
        'student_id': ('users.User', 'student'),
        'created_by_id': ('users.User', 'created_by'),
        'updated_by_id': ('users.User', 'updated_by'),
        'fee_item_id': ('finances.FeeItem', 'fee_item')
    }

    @classmethod
    def get_invoice(
            cls,
            invoice_id: str,
            status: Optional[str] = None,
            select_for_update: bool = False
    ) -> Invoice:
        """
        Retrieve a single invoice by ID, optionally filtering by status and/or
        locking for update.

        :param invoice_id: ID of the invoice to retrieve.
        :type invoice_id: str
        :param status: Optional status filter.
        :type status: str | None
        :param select_for_update: If True, lock the row for update.
        :type select_for_update: bool
        :raises Invoice.DoesNotExist: If the invoice does not exist.
        :return: Invoice instance.
        :rtype: Invoice
        """
        filters = Q(id=invoice_id)
        if status:
            filters &= Q(status=status.lower())

        qs = Invoice.objects
        if select_for_update:
            qs = qs.select_for_update()

        return qs.get(filters)

    @classmethod
    @transaction.atomic
    def create_invoice(cls, user: User, student_id: str, **data) -> Invoice:
        """
        Create a new invoice with invoice items for a student.

        :param user: User creating the invoice.
        :type user: User
        :param student_id: ID of the student the invoice is for.
        :type student_id: str
        :param data: Invoice data, including 'due_date', 'invoice_items', 'priority', and 'notes'.
        :type data: dict
        :raises ValidationError: If required fields are missing or invalid.
        :return: Created invoice instance.
        :rtype: Invoice
        """
        student = UserServices.get_user(user_id=student_id, role_name=RoleName.STUDENT)

        required_fields = {'due_date', 'invoice_items'}
        field_types = {'priority': int, 'invoice_items': list}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        invoice = Invoice.objects.create(
            student=student,
            priority=data.get('priority') or 1,
            due_date=data.get('due_date'),
            created_by=user,
            notes=data.get('notes')
        )

        for item_data in data.get('invoice_items'):
            fee_item_id = item_data.get('fee_item_id')
            unit_price = item_data.get('unit_price')
            quantity = item_data.get('quantity')
            description = item_data.get('description')

            required_fields = {'quantity'}
            field_types = {'unit_price': float, 'quantity': int}
            item_data = cls._sanitize_and_validate_data(
                item_data,
                required_fields=required_fields,
                field_types=field_types
            )

            fee_item = None
            if fee_item_id:
                fee_item = FeeItem.objects.get(id=fee_item_id, is_active=True)
                grade_level_fee = GradeLevelFee.objects.filter(
                    fee_item=fee_item,
                    grade_level=item_data.get('grade_level'),
                    term=item_data.get('term'),
                    academic_year=item_data.get('academic_year')
                ).first()
                unit_price = grade_level_fee.amount if grade_level_fee else fee_item.default_amount
            elif not unit_price:
                raise ValidationError('Fee item or unit price must be provided')

            unit_price = Decimal(unit_price)
            quantity = int(quantity)
            amount = unit_price * quantity

            InvoiceItem.objects.create(
                invoice=invoice,
                fee_item=fee_item,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                amount=amount
            )

        for student_guardian in invoice.student.student_guardians.filter(
                Q(is_primary=True) | Q(can_receive_reports=True), is_active=True):
            guardian = student_guardian.guardian
            notification_context = {
                "recipient_name": guardian.full_name,
                "student_full_name": invoice.student.full_name,
                "student_reg_number": invoice.student.reg_number,
                "invoice_reference": invoice.invoice_reference,
                "total_amount": f"{invoice.total_amount:,.2f}",
                "paid_amount": f"{invoice.paid_amount:,.2f}",
                "balance": f"{invoice.balance:,.2f}",
                "due_date": invoice.due_date,
                "invoice_status": invoice.status.upper(),
                "invoice_notes": invoice.notes,
                "current_year": timezone.now().year,
            }
            try:
                NotificationServices.send_notification(
                    recipients=[guardian.guardian_profile.email],
                    notification_type=NotificationType.EMAIL,
                    template_name='email_new_invoice',
                    context=notification_context,
                )
            except Exception as ex:
                logger.exception(f'Send new invoice notification error: {ex}')

        from .payment_services import PaymentServices
        # noinspection PyBroadException
        try:
            PaymentServices.allocate_payments(student.id)
        except:
            pass

        return invoice

    @classmethod
    @transaction.atomic
    def update_invoice(cls, user: User, invoice_id: str, **data) -> Invoice:
        """
        Update an existing invoice and its invoice items.

        :param user: User performing the update.
        :type user: User
        :param invoice_id: ID of the invoice to update.
        :type invoice_id: str
        :param data: Invoice data including updated 'invoice_items', 'priority', 'due_date', and 'notes'.
        :type data: dict
        :raises ValidationError: If required fields are missing or invalid.
        :return: Updated invoice instance.
        :rtype: Invoice
        """
        invoice = cls.get_invoice(invoice_id, select_for_update=True)

        required_fields = {'due_date', 'invoice_items'}
        field_types = {'priority': int, 'invoice_items': list}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        invoice.priority = data.get('priority') or 1
        invoice.due_date = data.get('due_date')
        invoice.notes = data.get('notes')
        invoice.updated_by = user
        invoice.save(update_fields=['priority', 'due_date', 'notes', 'updated_by'])

        InvoiceItem.objects.filter(invoice=invoice, is_active=True).update(is_active=False)

        for item_data in data.get('invoice_items'):
            fee_item_id = item_data.get('fee_item_id')
            unit_price = item_data.get('unit_price')
            quantity = item_data.get('quantity')
            description = item_data.get('description')

            required_fields = {'quantity'}
            field_types = {'unit_price': float, 'quantity': int}
            item_data = cls._sanitize_and_validate_data(
                item_data,
                required_fields=required_fields,
                field_types=field_types
            )

            fee_item = None
            if fee_item_id:
                fee_item = FeeItem.objects.get(id=fee_item_id, is_active=True)
                grade_level_fee = GradeLevelFee.objects.filter(
                    fee_item=fee_item,
                    grade_level=item_data.get('grade_level'),
                    term=item_data.get('term'),
                    academic_year=item_data.get('academic_year')
                ).first()
                unit_price = grade_level_fee.amount if grade_level_fee else fee_item.default_amount
            elif not unit_price:
                raise ValidationError('Fee item or unit price must be provided')

            InvoiceItem.objects.create(
                invoice=invoice,
                fee_item=fee_item,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
            )

        return invoice

    @classmethod
    @transaction.atomic
    def cancel_invoice(cls, user: User, invoice_id: str) -> Invoice:
        """
        Cancel an invoice and reverse all active payment allocations.

        :param user: User performing the cancellation.
        :type user: User
        :param invoice_id: ID of the invoice to cancel.
        :type invoice_id: str
        :return: Cancelled invoice instance.
        :rtype: Invoice
        """
        invoice = cls.get_invoice(invoice_id=invoice_id, select_for_update=True)

        # Deactivate payment allocations
        PaymentAllocation.objects.filter(
            invoice=invoice,
            is_active=True
        ).update(is_active=False)

        invoice.status = InvoiceStatus.CANCELLED
        invoice.updated_by = user
        invoice.save(update_fields=['status', 'updated_by'])

        return invoice

    @classmethod
    @transaction.atomic
    def activate_invoice(cls, user: User, invoice_id: str) -> Invoice:
        """
        Activate a cancelled invoice, setting its status to pending.

        :param user: User performing the activation.
        :type user: User
        :param invoice_id: ID of the invoice to activate.
        :type invoice_id: str
        :raises ValidationError: If invoice is already active.
        :return: Activated invoice instance.
        :rtype: Invoice
        """
        invoice = cls.get_invoice(invoice_id=invoice_id, select_for_update=True)
        if invoice.status != InvoiceStatus.CANCELLED:
            raise ValidationError('Invoice already active')

        invoice.status = InvoiceStatus.PENDING
        invoice.updated_by = user
        invoice.save(update_fields=['status', 'updated_by'])

        return invoice

    @classmethod
    def fetch_invoice(cls, invoice_id: str) -> dict:
        """
        Retrieve invoice details along with its items and payment allocations.

        :param invoice_id: ID of the invoice to fetch.
        :type invoice_id: str
        :return: Dictionary with invoice, student, items, and payment details.
        :rtype: dict
        """
        invoice = cls.get_invoice(invoice_id=invoice_id)

        invoice_items = list(
            InvoiceItem.objects
            .filter(invoice=invoice, is_active=True)
            .values()
        )

        payments = list(
            PaymentAllocation.objects
            .filter(invoice=invoice, is_active=True)
            .annotate(
                payment_reference=F('payment__payment_reference'),
                payment_method=F('payment__payment_method'),
            )
            .values()
        )

        classroom_assignment = invoice.student.student_classrooms.filter(is_current=True).first()

        return {
            'id': invoice.id,
            'invoice_reference': invoice.invoice_reference,
            'student_id': invoice.student.id,
            'student_reg_number': invoice.student.reg_number,
            'student_full_name': invoice.student.full_name,
            'student_classroom_id': classroom_assignment.classroom.id if classroom_assignment else None,
            'student_classroom_name': classroom_assignment.classroom.name if classroom_assignment else None,
            'student_grade_level': classroom_assignment.classroom.grade_level if classroom_assignment else None,
            'total_amount': invoice.total_amount,
            'paid_amount': invoice.paid_amount,
            'balance': invoice.balance,
            'priority': invoice.priority,
            'due_date': invoice.due_date,
            'created_by_id': invoice.created_by.id,
            'created_by_reg_number': invoice.created_by.reg_number,
            'created_by_full_name': invoice.created_by.full_name,
            'updated_by_id': invoice.updated_by.id if invoice.updated_by else None,
            'updated_by_reg_number': invoice.updated_by.reg_number if invoice.updated_by else None,
            'updated_by_full_name': invoice.updated_by.full_name if invoice.updated_by else None,
            'notes': invoice.notes,
            'is_auto_generated': invoice.is_auto_generated,
            'status': invoice.computed_status,
            'created_at': invoice.created_at,
            'updated_at': invoice.updated_at,
            'invoice_items': invoice_items,
            'payments': payments
        }

    @classmethod
    def filter_invoices(cls, **filters) -> list[dict]:
        """
        Filter invoices based on fields and a search term.

        :param filters: Keyword arguments containing invoice fields and optional 'search_term'.
        :return: List of invoice dictionaries matching filters.
        :rtype: list[dict]
        """
        field_types = {'priority': int}
        filters = cls._sanitize_and_validate_data(filters, field_types=field_types)

        invoice_field_names = {f.name for f in Invoice._meta.get_fields()}
        cleaned_filters = {k: v for k, v in filters.items() if k in invoice_field_names}

        qs = Invoice.objects.filter(student__is_active=True, **cleaned_filters).order_by('-created_at')

        search_term = filters.get('search_term')
        if search_term:
            fields = [
                'invoice_reference',
                'student__id',
                'student__reg_number',
                'student__first_name',
                'student__last_name',
                'status',
            ]
            search_q = Q()

            for field in fields:
                search_q |= Q(**{f'{field}__icontains': search_term})

            qs = qs.filter(search_q)

        fee_item = filters.get('fee_item')
        if fee_item:
            qs = qs.filter(
                items__fee_item=fee_item,
                items__is_active=True
            ).distinct()

        invoice_ids = qs.values_list('id', flat=True)
        return [cls.fetch_invoice(invoice_id) for invoice_id in invoice_ids]

    @classmethod
    @transaction.atomic
    def bulk_create_invoices(cls, user: User, student_ids: list[str], invoice_data: dict) -> dict:
        if not isinstance(student_ids, list) or len(student_ids) == 0:
            raise ValidationError('student_ids must be a non-empty list')

        if len(student_ids) > 500:
            raise ValidationError('Cannot process more than 500 students at once')

        required_fields = {'description', 'due_date', 'invoice_items'}
        field_types = {'priority': int, 'invoice_items': list}
        invoice_data = cls._sanitize_and_validate_data(
            invoice_data,
            required_fields=required_fields,
            field_types=field_types
        )

        students = User.objects.filter(
            school=user.school,
            role__name=RoleName.STUDENT,
            id__in=student_ids,
            is_active=True
        )

        if len(students) != len(student_ids):
            missing = set(student_ids) - {str(s.id) for s in students}
            raise ValidationError(f"Students not found or inactive: {missing}")

        created_invoices = []
        total_amount = Decimal('0.00')

        for student in students:
            invoice = Invoice.objects.create(
                student=student,
                priority=invoice_data.get('priority', 1),
                due_date=invoice_data.get('due_date'),
                created_by=user,
                notes=invoice_data.get('notes'),
                is_auto_generated=True
            )

            invoice_total = Decimal('0.00')
            for item_data in invoice_data.get('invoice_items'):
                fee_item_id = item_data.get('fee_item_id')
                unit_price = item_data.get('unit_price')
                quantity = item_data.get('quantity', 1)
                description = item_data.get('description', '')

                required_fields = {'quantity'}
                field_types = {'unit_price': float, 'quantity': int}
                item_data_clean = cls._sanitize_and_validate_data(
                    item_data,
                    required_fields=required_fields,
                    field_types=field_types
                )

                fee_item = None
                if fee_item_id:
                    fee_item = FeeItem.objects.get(id=fee_item_id, is_active=True)
                    grade_level_fee = GradeLevelFee.objects.filter(
                        fee_item=fee_item,
                        grade_level=item_data_clean.get('grade_level'),
                        term=item_data_clean.get('term'),
                        academic_year=item_data_clean.get('academic_year')
                    ).first()
                    unit_price = grade_level_fee.amount if grade_level_fee else fee_item.default_amount
                elif not unit_price:
                    raise ValidationError('Fee item or unit price must be provided')

                unit_price = Decimal(str(unit_price))
                quantity = int(quantity)
                amount = unit_price * quantity
                invoice_total += amount

                InvoiceItem.objects.create(
                    invoice=invoice,
                    fee_item=fee_item,
                    description=description,
                    quantity=quantity,
                    unit_price=unit_price,
                    amount=amount
                )

            created_invoices.append(invoice)
            total_amount += invoice_total

        bulk_invoice = BulkInvoice.objects.create(
            bulk_reference=BulkInvoice.generate_bulk_reference(),
            created_by=user,
            description=invoice_data.get('description', ''),
            notes=invoice_data.get('notes', ''),
            student_count=len(students),
            invoice_count=len(created_invoices),
            total_amount=total_amount,
            due_date=invoice_data.get('due_date'),
            priority=invoice_data.get('priority', 1),
        )
        bulk_invoice.invoices.set(created_invoices)

        return {
            'bulk_invoice': bulk_invoice,
            'invoices': created_invoices
        }

    @classmethod
    @transaction.atomic
    def bulk_cancel_invoices(cls, user: User, bulk_invoice_id: str, reason: str = '') -> BulkInvoice:
        bulk_invoice = BulkInvoice.objects.select_related(
            'created_by'
        ).prefetch_related('invoices').get(id=bulk_invoice_id)

        bulk_invoice.cancel(cancelled_by=user, reason=reason)

        return bulk_invoice

    @classmethod
    def fetch_bulk_invoice(cls, bulk_invoice_id: str) -> dict:
        bulk = BulkInvoice.objects.select_related(
            'created_by', 'cancelled_by'
        ).prefetch_related(
            'invoices__student',
            'invoices__items__fee_item'
        ).get(id=bulk_invoice_id)

        invoice_details = []
        for invoice in bulk.invoices.all():
            invoice_details.append({
                'id': str(invoice.id),
                'invoice_reference': invoice.invoice_reference,
                'student_id': str(invoice.student.id),
                'student_full_name': invoice.student.full_name,
                'student_reg_number': invoice.student.reg_number,
                'total_amount': float(invoice.total_amount),
                'paid_amount': float(invoice.paid_amount),
                'balance': float(invoice.balance),
                'status': invoice.status,
                'due_date': invoice.due_date,
                'items': [
                    {
                        'description': item.description or item.fee_item.name if item.fee_item else '',
                        'quantity': item.quantity,
                        'unit_price': float(item.unit_price),
                        'amount': float(item.amount)
                    }
                    for item in invoice.items.filter(is_active=True)
                ]
            })

        return {
            'bulk_invoice': {
                'id': str(bulk.id),
                'bulk_reference': bulk.bulk_reference,
                'created_by': bulk.created_by.full_name,
                'created_at': bulk.created_at,
                'student_count': bulk.student_count,
                'invoice_count': bulk.invoice_count,
                'total_amount': str(bulk.total_amount),
                'due_date': bulk.due_date,
                'priority': bulk.priority,
                'description': bulk.description,  # ← Added
                'notes': bulk.notes,
                'is_cancelled': bulk.is_cancelled,
                'cancelled_by': bulk.cancelled_by.full_name if bulk.cancelled_by else None,
                'cancelled_at': bulk.cancelled_at,
                'cancellation_reason': bulk.cancellation_reason or None,
            },
            'invoices': invoice_details
        }

    @classmethod
    def list_bulk_invoices(cls, **filters) -> list[dict]:
        qs = BulkInvoice.objects.select_related('created_by').order_by('-created_at')

        search_term = filters.get('search_term')
        if search_term:
            qs = qs.filter(
                Q(bulk_reference__icontains=search_term) |
                Q(created_by__full_name__icontains=search_term) |
                Q(notes__icontains=search_term)
            )

        return [
            {
                'id': str(b.id),
                'bulk_reference': b.bulk_reference,
                'created_by': b.created_by.full_name,
                'created_at': b.created_at,
                'student_count': b.student_count,
                'invoice_count': b.invoice_count,
                'total_amount': str(b.total_amount),
                'due_date': b.due_date,
                'description': b.description,
                'notes': b.notes,
                'is_cancelled': b.is_cancelled,
            }
            for b in qs
        ]

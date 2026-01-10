import logging

from decimal import Decimal
from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, F, Subquery, OuterRef, Sum, FloatField, Value, CharField
from django.db.models.functions import Coalesce, Concat
from django.utils import timezone

from base.services.base_services import BaseServices
from finances.models import (
    Payment,
    PaymentAllocation,
    MpesaTransaction,
    Refund,
    PaymentStatus,
    PaymentMethod,
    InvoiceItem, RefundStatus, Invoice, InvoiceStatus
)
from notifications.models import NotificationType
from notifications.services.notification_services import NotificationServices
from users.models import User, RoleName
from users.services.user_services import UserServices

logger = logging.getLogger(__name__)


class PaymentServices(BaseServices):
    """
    Service class that handles creation, retrieval, reversing, refunding, approving, and querying of payment records.
    """

    fk_mappings = {
        'student_id': ('users.User', 'student'),
        'verified_by_id': ('users.User', 'verified_by'),
        'priority_invoice_id': ('finances.Invoice', 'priority_invoice')
    }

    @classmethod
    def get_payment(
        cls,
        payment_id: str,
        status: Optional[str] = None,
        select_for_update: bool = False
    ) -> Payment:
        print(payment_id)
        filters = Q(id=payment_id)
        if status:
            filters &= Q(status=status.upper())

        qs = Payment.objects
        if select_for_update:
            qs = qs.select_for_update()

        print(filters)

        return qs.get(filters)

    @classmethod
    def create_payment(cls, created_by: User, student_id: str, **data) -> Payment:
        print(data)
        student = UserServices.get_user(
            user_id=student_id,
            role_name=RoleName.STUDENT
        )

        required_fields = {'payment_method', 'amount'}
        field_types = {'amount': float}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        payment_method = data.get('payment_method')
        if payment_method not in PaymentMethod.values:
            raise ValidationError('Invalid payment method')

        if payment_method == PaymentMethod.MPESA:
            required_mpesa = {'mpesa_receipt_number', 'mpesa_phone_number', 'mpesa_transaction_date'}
            missing = required_mpesa - set(data.keys())
            if missing:
                raise ValidationError(f"Missing required M-Pesa fields: {', '.join(missing)}")

        elif payment_method == PaymentMethod.BANK:
            required_bank = {'bank_reference', 'bank_name'}
            missing = required_bank - set(data.keys())
            if missing:
                raise ValidationError(f"Missing required bank fields: {', '.join(missing)}")

        # Manual payments are auto-approved
        status = PaymentStatus.COMPLETED
        verified_by = created_by
        verified_at = timezone.now()
        notes = data.get('notes', '')

        payment = Payment.objects.create(
            **data,
            student=student,
            verified_by=verified_by,
            verified_at=verified_at,
            status=status,
            notes=notes
        )

        for student_guardian in student.student_guardians.filter(
                Q(is_primary=True) | Q(can_receive_reports=True), is_active=True):
            guardian = student_guardian.guardian
            notification_context = {
                "recipient_name": guardian.full_name,
                "student_full_name": student.full_name,
                "student_reg_number": student.reg_number,
                "payment_reference": payment.payment_reference,
                "payment_method": payment.payment_method.title(),
                "amount": f"{payment.amount:,.2f}",
                "payment_date": str(payment.created_at.date()),
                "payment_status": payment.status.title(),
                "payment_action": "approved" if payment.verified_at else "recorded",
                "current_year": timezone.now().year,
            }
            try:
                NotificationServices.send_notification(
                    recipients=[guardian.guardian_profile.email],
                    notification_type=NotificationType.EMAIL,
                    template_name='email_new_payment',
                    context=notification_context,
                )
            except Exception as ex:
                logger.exception(f'Send new payment notification error: {ex}')

        # noinspection PyBroadException
        try:
            cls.allocate_payments(payment.student.id)
        except:
            pass

        return payment

    @classmethod
    def create_pending_payment(cls, student_id: str, **data) -> Payment:
        """
        Create a payment with PENDING status (e.g. from M-Pesa STK push or callback).
        These are auto-generated and require manual approval.
        """
        student = UserServices.get_user(
            user_id=student_id,
            role_name=RoleName.STUDENT
        )

        data = cls._sanitize_and_validate_data(
            data,
            required_fields={'payment_method', 'amount'},
            field_types={'amount': float}
        )

        payment = Payment.objects.create(
            **data,
            student=student,
            status=PaymentStatus.PENDING,
            notes=data.get('notes', 'Auto-generated pending payment')
        )

        return payment

    @classmethod
    def approve_payment(cls, approved_by: User, payment_id: str) -> Payment:
        """
        Approve a PENDING payment → set to COMPLETED and record verifier.
        """
        payment = cls.get_payment(payment_id=payment_id, status=PaymentStatus.PENDING, select_for_update=True)

        with transaction.atomic():
            payment.status = PaymentStatus.COMPLETED
            payment.verified_by = approved_by
            payment.verified_at = timezone.now()
            payment.save(update_fields=['status', 'verified_by', 'verified_at'])

        for student_guardian in payment.student.student_guardians.filter(
                Q(is_primary=True) | Q(can_receive_reports=True), is_active=True):
            guardian = student_guardian.guardian
            notification_context = {
                "recipient_name": guardian.full_name,
                "student_full_name": payment.student.full_name,
                "student_reg_number": payment.student.reg_number,
                "payment_reference": payment.payment_reference,
                "payment_method": payment.payment_method.title(),
                "amount": f"{payment.amount:,.2f}",
                "payment_date": str(payment.created_at.date()),
                "payment_status": payment.status.title(),
                "payment_action": "approved" if payment.verified_at else "recorded",
                "current_year": timezone.now().year,
            }
            try:
                NotificationServices.send_notification(
                    recipients=[guardian.guardian_profile.email],
                    notification_type=NotificationType.EMAIL,
                    template_name='email_new_payment',
                    context=notification_context,
                )
            except Exception as ex:
                logger.exception(f'Send new payment notification error: {ex}')

        # noinspection PyBroadException
        try:
            cls.allocate_payments(payment.student.id)
        except:
            pass


        return payment

    @classmethod
    def reverse_payment(cls, reversed_by: User, payment_id: str, reverse_reason: str) -> None:
        payment = cls.get_payment(payment_id=payment_id, select_for_update=True)
        payment.reverse_payment(reversed_by=reversed_by, reason=reverse_reason or 'Not provided')

    @classmethod
    def create_refund(cls, refunded_by: User, payment_id: str, **data) -> Refund:
        payment = cls.get_payment(payment_id=payment_id)

        if payment.status != PaymentStatus.COMPLETED:
            raise ValidationError("Refunds can only be issued on COMPLETED payments")

        amount = Decimal(data.pop('amount'))
        refund_method = data.pop('refund_method')

        return payment.create_refund(
            amount=amount,
            refund_method=refund_method,
            processed_by=refunded_by,
            **data
        )

    @classmethod
    def cancel_refund(cls, cancelled_by: User, refund_id: str, reason: str = '') -> Refund:
        refund = Refund.objects.select_for_update().get(id=refund_id)

        if refund.status == RefundStatus.CANCELLED:
            raise ValidationError("Refund is already cancelled")

        refund.cancel_refund(cancelled_by=cancelled_by, reason=reason)
        return refund

    @classmethod
    def fetch_payment(cls, payment_id: str) -> dict:
        payment = cls.get_payment(payment_id)

        allocations = list(
            PaymentAllocation.objects
            .filter(payment=payment, is_active=True)
            .annotate(
                invoice_reference=F('invoice__invoice_reference'),
                invoice_due_date=F('invoice__due_date'),
                invoice_status=F('invoice__status'),
                invoice_total_amount=Subquery(
                    InvoiceItem.objects.filter(
                        invoice_id=OuterRef('invoice_id'),
                        is_active=True
                    )
                    .values('invoice_id')
                    .annotate(total=Sum('amount'))
                    .values('total')[:1],
                    output_field=FloatField()
                ),
                invoice_paid_amount=Subquery(
                    PaymentAllocation.objects.filter(
                        invoice_id=OuterRef('invoice_id'),
                        is_active=True
                    )
                    .values('invoice_id')
                    .annotate(paid=Sum('allocated_amount'))
                    .values('paid')[:1],
                    output_field=FloatField()
                ),
            )
            .annotate(
                invoice_balance=F('invoice_total_amount') - F('invoice_paid_amount')
            )
            .values(
                'id', 'allocated_amount', 'allocation_order',
                'invoice_reference', 'invoice_total_amount',
                'invoice_paid_amount', 'invoice_balance',
                'invoice_due_date', 'invoice_status'
            )
        )

        refunds = list(
            Refund.objects.filter(original_payment=payment)
            .select_related('processed_by')
            .annotate(
                processed_by_full_name=Coalesce(
                    Concat(
                        F('processed_by__first_name'),
                        Value(' '),
                        F('processed_by__last_name'),
                        Value(' '),
                        F('processed_by__other_name'),
                        output_field=CharField()
                    ),
                    Value('—'),
                    output_field=CharField()
                )
            )
            .values(
                'id',
                'amount',
                'refund_method',
                'status',
                'processed_at',
                'mpesa_receipt_number',
                'bank_reference',
                'notes',
                'processed_by_full_name',
                # 'cancelled_by_full_name',
                'cancellation_reason',
                'cancelled_at',
            )
        )

        mpesa_transactions = list(
            MpesaTransaction.objects
            .filter(payment=payment)
            .values()
        )

        return {
            'id': str(payment.id),
            'payment_reference': payment.payment_reference,
            'student_id': str(payment.student.id) if payment.student else None,
            'student_reg_number': payment.student.reg_number if payment.student else None,
            'student_full_name': payment.student.full_name if payment.student else None,
            'payment_method': payment.payment_method,
            'amount': float(payment.amount),
            'allocated_amount': float(payment.allocated_amount),
            'effective_utilized_amount': float(payment.effective_utilized_amount),
            'completed_refunded_amount': float(payment.completed_refunded_amount),
            'pending_refunded_amount': float(payment.pending_refunded_amount),
            'unassigned_amount': float(payment.unassigned_amount),
            'available_for_refund': float(payment.get_available_refund_amount),
            'mpesa_receipt_number': payment.mpesa_receipt_number,
            'mpesa_phone_number': payment.mpesa_phone_number,
            'mpesa_transaction_date': payment.mpesa_transaction_date,
            'bank_reference': payment.bank_reference,
            'bank_name': payment.bank_name,
            'transaction_id': payment.transaction_id,
            'verified_at': payment.verified_at,
            'verified_by_id': str(payment.verified_by.id) if payment.verified_by else None,
            'verified_by_full_name': payment.verified_by.full_name if payment.verified_by else None,
            'reversed_by_id': str(payment.reversed_by.id) if payment.reversed_by else None,
            'reversed_by_full_name': str(payment.reversed_by.full_name) if payment.reversed_by else None,
            'reversed_at': payment.reversed_at,
            'reversal_reason': payment.reversal_reason,
            'notes': payment.notes,
            'metadata': payment.metadata,
            'status': payment.status,
            'created_at': payment.created_at,
            'updated_at': payment.updated_at,
            'payment_allocations': allocations,
            'refunds': refunds,
            'mpesa_transactions': mpesa_transactions
        }

    @classmethod
    def filter_payments(cls, filtered_by: User, **filters) -> list[dict]:
        filters = cls._sanitize_and_validate_data(filters)

        payment_field_names = {f.name for f in Payment._meta.get_fields()}
        cleaned_filters = {k: v for k, v in filters.items() if k in payment_field_names}

        qs = Payment.objects.filter(
            student__school=filtered_by.school,
            student__is_active=True,
            **cleaned_filters
        ).order_by('-created_at')

        search_term = filters.get('search_term')
        if search_term:
            search_q = Q()
            fields = [
                'payment_reference',
                'student__reg_number',
                'student__first_name',
                'student__last_name',
                'mpesa_receipt_number',
                'bank_reference',
                'transaction_id',
            ]
            for field in fields:
                search_q |= Q(**{f'{field}__icontains': search_term})
            qs = qs.filter(search_q)

        payment_ids = qs.values_list('id', flat=True)
        return [cls.fetch_payment(str(pid)) for pid in payment_ids]

    @classmethod
    @transaction.atomic
    def allocate_payments(cls, student_id: str) -> None:
        student = UserServices.get_user(user_id=student_id, role_name=RoleName.STUDENT)

        # Fetch allocatable payments
        payments = (
            Payment.objects
            .select_for_update()
            .filter(
                student=student,
                status__in=[PaymentStatus.COMPLETED, PaymentStatus.PARTIALLY_REFUNDED],
            )
            .order_by('created_at')
        )
        payments = [p for p in payments if p.unassigned_amount > 0]

        if not payments:
            return

        # Fetch allocatable invoices
        invoices = (
            Invoice.objects
            .select_for_update()
            .filter(
                ~Q( status__in=[InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED]),
                student=student,
            )
            .order_by('priority', 'due_date', 'created_at')
        )
        invoices = [inv for inv in invoices if inv.balance > 0]

        if not invoices:
            return

        invoice_map = {inv.id: inv for inv in invoices}

        for payment in payments:
            remaining_payment_amount = Decimal(payment.unassigned_amount)

            if remaining_payment_amount <= 0:
                continue

            allocation_counter = 1

            # ---- Step 1: Allocate to priority invoice first ----
            if payment.priority_invoice_id:
                priority_invoice = invoice_map.get(payment.priority_invoice_id)

                if (
                        priority_invoice
                        and priority_invoice.status in [InvoiceStatus.PENDING, InvoiceStatus.PARTIAL]
                        and priority_invoice.balance > 0
                ):
                    allocation_amount = min(
                        remaining_payment_amount,
                        Decimal(priority_invoice.balance)
                    )

                    PaymentAllocation.objects.create(
                        payment=payment,
                        invoice=priority_invoice,
                        allocated_amount=allocation_amount,
                        allocation_order=allocation_counter
                    )

                    allocation_counter += 1
                    remaining_payment_amount -= allocation_amount
                    priority_invoice.refresh_from_db()
                    priority_invoice.update_status()

            # ---- Step 2: Allocate any remaining amount to other invoices ----
            for invoice in invoices:
                if remaining_payment_amount <= 0:
                    break

                # Skip priority invoice if already handled
                if payment.priority_invoice_id and invoice.id == payment.priority_invoice_id:
                    continue

                if invoice.balance <= 0:
                    continue

                allocation_amount = min(
                    remaining_payment_amount,
                    Decimal(invoice.balance)
                )

                PaymentAllocation.objects.create(
                    payment=payment,
                    invoice=invoice,
                    allocated_amount=allocation_amount,
                    allocation_order=allocation_counter
                )

                allocation_counter += 1
                remaining_payment_amount -= allocation_amount
                invoice.refresh_from_db()
                invoice.update_status()

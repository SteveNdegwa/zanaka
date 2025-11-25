from typing import Optional

from django.core.exceptions import ValidationError
from django.db.models import Q, F
from django.utils import timezone

from base.services.base_services import BaseServices
from finances.models import Payment, PaymentAllocation, MpesaTransaction, PaymentStatus, PaymentMethod
from users.models import User, RoleName
from users.services.user_services import UserServices


class PaymentServices(BaseServices):
    """
    Service class that handles creation, retrieval, reversing, and querying of payment records.
    """

    fk_mappings = {
        "student_id": ("users.User", "student"),
        "verified_by_id": ("users.User", "verified_by"),
    }

    @classmethod
    def get_payment(
        cls,
        payment_id: str,
        status: Optional[str] = None,
        select_for_update: bool = False
    ) -> Payment:
        """
        Retrieve a payment by ID, optionally restricting by status and applying
        row-level locking.

        :param payment_id: The ID of the payment to retrieve.
        :type payment_id: str
        :param status: Optional status to filter the payment.
        :type status: str, optional
        :param select_for_update: Whether to lock the record using SELECT FOR UPDATE.
        :type select_for_update: bool
        :raises Payment.DoesNotExist: If the payment does not exist.
        :raises Payment.MultipleObjectsReturned: If more than one payment matches.
        :rtype: Payment
        """
        filters = Q(id=payment_id)
        if status:
            filters &= Q(status=status.lower())

        qs = Payment.objects
        if select_for_update:
            qs = qs.select_for_update()

        return qs.get(filters)

    @classmethod
    def create_payment(cls, user: User, student_id: str, **data) -> Payment:
        """
        Creates a new payment after validating the provided data based on the
        selected payment method.

        :param user: The user verifying the payment.
        :type user: User
        :param student_id: The ID of the student receiving the payment.
        :type student_id: str
        :param data: Incoming payment fields.
        :type data: dict
        :raises ValidationError: Raised when required fields are missing or invalid
            for the selected payment method.
        :rtype: Payment
        """

        student = UserServices.get_user(
            user_id=student_id,
            role_name=RoleName.STUDENT
        )

        required_fields = {"payment_method", "amount"}
        field_types = {"amount": float}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        payment_method = data.get("payment_method")
        if payment_method not in PaymentMethod.values:
            raise ValidationError("Invalid payment method")

        if payment_method == PaymentMethod.MPESA:
            required_fields = {"mpesa_receipt_number", "mpesa_phone_number", "mpesa_transaction_date"}
            for field in required_fields:
                if not data.get(field):
                    field_name = field.replace("_", " ").capitalize()
                    raise ValidationError(f"{field_name} must be provided")

        elif payment_method == PaymentMethod.BANK:
            required_fields = {"bank_reference", "bank_name"}
            for field in required_fields:
                if not data.get(field):
                    field_name = field.replace("_", " ").capitalize()
                    raise ValidationError(f"{field_name} must be provided")

        payment = Payment.objects.create(
            **data,
            student=student,
            verified_by=user,
            verified_at=timezone.now()
        )

        return payment

    @classmethod
    def reverse_payment(cls, payment_id: str) -> None:
        """
        Reverse a payment by updating its status and deactivating all active allocations.

        :param payment_id: The ID of the payment to reverse.
        :type payment_id: str
        :raises Payment.DoesNotExist: If the payment does not exist.
        :rtype: None
        """
        payment = cls.get_payment(payment_id=payment_id, select_for_update=True)
        payment.status = PaymentStatus.REVERSED
        payment.save(update_fields=["status"])

    @classmethod
    def fetch_payment(cls, payment_id: str) -> dict:
        """
        Retrieve a payment and its related allocations and MPESA transactions.

        :param payment_id: The ID of the payment to fetch.
        :type payment_id: str
        :raises Payment.DoesNotExist: If the payment does not exist.
        :rtype: dict
        """
        payment = cls.get_payment(payment_id)

        allocations = list(
            PaymentAllocation.objects
            .filter(payment=payment, is_active=True)
            .annotate(
                invoice_reference=F("invoice__invoice_reference"),
                invoice_total_amount=F("invoice__total_amount"),
                invoice_paid_amount=F("invoice__paid_amount"),
                invoice_balancet=F("invoice__balance"),
                invoice_due_date=F("invoice__due_date"),
                invoice_status=F("invoice__status"),
            )
            .values()
        )

        mpesa_transactions = list(
            MpesaTransaction.objects
            .filter(payment=payment)
            .values()
        )

        return {
            "id": str(payment.id),
            "payment_reference": payment.payment_reference,
            "student_id": str(payment.student.id),
            "student_reg_number": payment.student.reg_number,
            "student_full_name": payment.student.full_name,
            "payment_method": payment.payment_method,
            "amount": payment.amount,
            "utilized_amount": payment.utilized_amount,
            "mpesa_receipt_number": payment.mpesa_receipt_number,
            "mpesa_phone_number": payment.mpesa_phone_number,
            "mpesa_transaction_date": payment.mpesa_transaction_date,
            "bank_reference": payment.bank_reference,
            "bank_name": payment.bank_name,
            "transaction_id": payment.transaction_id,
            "verified_at": payment.verified_at,
            "verified_by_id": str(payment.verified_by.id),
            "verified_by_reg_number": payment.verified_by.reg_number,
            "verified_by_full_name": payment.verified_by.full_name,
            "notes": payment.notes,
            "metadata": payment.metadata,
            "status": payment.status,
            "created_at": payment.created_at,
            "payment_allocations": allocations,
            "mpesa_transactions": mpesa_transactions
        }

    @classmethod
    def filter_payments(cls, **filters) -> list[dict]:
        """
        Filter payments using provided field filters and optional free-text search.

        :param filters: Filtering parameters including search_term and field filters.
        :type filters: dict
        :rtype: list[dict]
        """
        filters = cls._sanitize_and_validate_data(filters)

        payment_field_names = set(Payment._meta.fields_map.keys())
        cleaned_filters = {k: v for k, v in filters.items() if k in payment_field_names}

        qs = Payment.objects.filter(**cleaned_filters)

        search_term = filters.get("search_term")
        if search_term:
            fields = [
                "payment_reference",
                "student__id",
                "student__reg_number",
                "student__first_name",
                "student__last_name",
                "payment_method",
                "mpesa_receipt_number",
                "mpesa_phone_number",
                "bank_reference",
                "bank_name",
                "transaction_id",
                "status",
            ]

            search_q = Q()
            for field in fields:
                search_q |= Q(**{f"{field}__icontains": search_term})

            qs = qs.filter(search_q)

        payment_ids = qs.values_list("id", flat=True)
        return [cls.fetch_payment(payment_id) for payment_id in payment_ids]

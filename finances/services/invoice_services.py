from typing import Optional

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, F

from base.services.base_services import BaseServices
from finances.models import Invoice, FeeItem, GradeLevelFee, InvoiceItem, PaymentAllocation, InvoiceStatus
from users.models import User, RoleName
from users.services.user_services import UserServices


class InvoiceServices(BaseServices):
    """
    Service layer for managing invoices, including creation, update, cancellation,
    activation, fetching, and filtering.
    """

    fk_mappings = {
        "student_id": ("users.User", "student"),
        "created_by_id": ("users.User", "created_by"),
        "updated_by_id": ("users.User", "updated_by"),
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

        required_fields = {"due_date", "invoice_items"}
        field_types = {"priority": int, "invoice_items": list}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        invoice = Invoice.objects.create(
            student=student,
            priority=data.get("priority") or 1,
            due_date=data.get("due_date"),
            created_by=user,
            notes=data.get("notes")
        )

        total_amount = 0
        for item_data in data.get("invoice_items"):
            fee_item_id = item_data.get("fee_item_id")
            unit_price = item_data.get("unit_price")
            quantity = item_data.get("quantity")
            description = item_data.get("description")

            required_fields = {"quantity"}
            field_types = {"unit_price": float, "quantity": int}
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
                    grade_level=item_data.get("grade_level"),
                    term=item_data.get("term"),
                    academic_year=item_data.get("academic_year")
                ).first()
                unit_price = grade_level_fee.amount if grade_level_fee else fee_item.default_amount
            elif not unit_price:
                raise ValidationError("Fee item or unit price must be provided")

            amount = unit_price * quantity

            InvoiceItem.objects.create(
                invoice=invoice,
                fee_item=fee_item,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                amount=amount
            )

            total_amount += amount

        invoice.total_amount = total_amount
        invoice.save(update_fields=["total_amount"])

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

        required_fields = {"due_date", "invoice_items"}
        field_types = {"priority": int, "invoice_items": list}
        data = cls._sanitize_and_validate_data(
            data,
            required_fields=required_fields,
            field_types=field_types
        )

        invoice.priority = data.get("priority") or 1
        invoice.due_date = data.get("due_date")
        invoice.notes = data.get("notes")

        InvoiceItem.objects.filter(invoice=invoice, is_active=True).update(is_active=False)

        total_amount = 0
        for item_data in data.get("invoice_items"):
            fee_item_id = item_data.get("fee_item_id")
            unit_price = item_data.get("unit_price")
            quantity = item_data.get("quantity")
            description = item_data.get("description")

            required_fields = {"quantity"}
            field_types = {"unit_price": float, "quantity": int}
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
                    grade_level=item_data.get("grade_level"),
                    term=item_data.get("term"),
                    academic_year=item_data.get("academic_year")
                ).first()
                unit_price = grade_level_fee.amount if grade_level_fee else fee_item.default_amount
            elif not unit_price:
                raise ValidationError("Fee item or unit price must be provided")

            amount = unit_price * quantity

            InvoiceItem.objects.create(
                invoice=invoice,
                fee_item=fee_item,
                description=description,
                quantity=quantity,
                unit_price=unit_price,
                amount=amount
            )

            total_amount += amount

        invoice.total_amount = total_amount
        invoice.updated_by = user
        invoice.save(update_fields=["priority", "due_date", "notes", "total_amount", "updated_by"])

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

        # Reverse payment allocations
        allocations = PaymentAllocation.objects.filter(invoice=invoice, is_active=True)
        for allocation in allocations:
            payment = allocation.payment
            payment.utilized_amount -= allocation.allocated_amount
            payment.save(update_fields=["utilized_amount"])

            allocation.is_active = False
            allocation.save(update_fields=["is_active"])

        invoice.status = InvoiceStatus.CANCELLED
        invoice.updated_by = user
        invoice.save(update_fields=["status", "updated_by"])

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
            raise ValidationError("Invoice already active")

        invoice.status = InvoiceStatus.PENDING
        invoice.updated_by = user
        invoice.save(update_fields=["status", "updated_by"])

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
                payment_reference=F("payment__payment_reference"),
                payment_method=F("payment__payment_method"),
            )
            .values()
        )

        return {
            "id": str(invoice.id),
            "invoice_reference": invoice.invoice_reference,
            "student_id": str(invoice.student.id),
            "student_reg_number": invoice.student.reg_number,
            "student_full_name": invoice.student.full_name,
            "student_classroom_id": str(invoice.student.classroom.id),
            "student_classroom_name": invoice.student.classroom.name,
            "total_amount": invoice.total_amount,
            "paid_amount": invoice.paid_amount,
            "balance": invoice.balance,
            "priority": invoice.priority,
            "due_date": invoice.due_date,
            "created_by_id": str(invoice.created_by.id),
            "created_by_reg_number": invoice.created_by.reg_number,
            "created_by_full_name": invoice.created_by.full_name,
            "updated_by_id": str(invoice.updated_by.id),
            "updated_by_reg_number": invoice.updated_by.reg_number,
            "updated_by_full_name": invoice.updated_by.full_name,
            "notes": invoice.notes,
            "is_auto_generated": invoice.is_auto_generated,
            "status": invoice.status,
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at,
        }

    @classmethod
    def filter_invoices(cls, **filters) -> list[dict]:
        """
        Filter invoices based on fields and a search term.

        :param filters: Keyword arguments containing invoice fields and optional 'search_term'.
        :type filters: dict
        :return: List of invoice dictionaries matching filters.
        :rtype: list[dict]
        """
        field_types = {"priority": int}
        filters = cls._sanitize_and_validate_data(filters, field_types=field_types)

        invoice_field_names = set(Invoice._meta.fields_map.keys())
        cleaned_filters = {k: v for k, v in filters.items() if k in invoice_field_names}

        qs = Invoice.objects.filter(**cleaned_filters)

        search_term = filters.get("search_term")
        if search_term:
            search_q = Q(invoice_reference__icontains=search_term)
            search_q |= Q(student__id__icontains=search_term)
            search_q |= Q(student__reg_number__icontains=search_term)
            search_q |= Q(student__first_name__icontains=search_term)
            search_q |= Q(student__last_name__icontains=search_term)
            search_q |= Q(status__icontains=search_term)

            qs = qs.filter(search_q)

        invoice_ids = qs.values_list("id", flat=True)
        return [cls.fetch_invoice(invoice_id) for invoice_id in invoice_ids]

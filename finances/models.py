from decimal import Decimal

from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel, GenericBaseModel
from schools.models import GradeLevel, School, Branch
from users.models import User, RoleName


class FeeItemCategory(models.TextChoices):
    TUITION = 'TUITION', _('Tuition Fees')
    TRANSPORT = 'TRANSPORT', _('Transport Fees')
    ACTIVITY = 'ACTIVITY', _('Activity Fees')
    UNIFORM = 'UNIFORM', _('Uniform')
    OTHER = 'OTHER', _('Other')


class Term(models.TextChoices):
    TERM_1 = 'TERM_1', _('Term 1')
    TERM_2 = 'TERM_2', _('Term 2')
    TERM_3 = 'TERM_3', _('Term 3')


class InvoiceStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    PENDING = 'PENDING', _('Pending')
    PARTIALLY_PAID = 'PARTIALLY_PAID', _('Partially Paid')
    PAID = 'PAID', _('Paid')
    OVERDUE = 'OVERDUE', _('Overdue')
    CANCELLED = 'CANCELLED', _('Cancelled')


class PaymentMethod(models.TextChoices):
    MPESA = 'MPESA', _('M-Pesa')
    BANK = 'BANK', _('Bank Transfer')
    CASH = 'CASH', _('Cash')
    CHEQUE = 'CHEQUE', _('Cheque')
    CARD = 'CARD', _('Card')


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    COMPLETED = 'COMPLETED', _('Completed')
    FAILED = 'FAILED', _('Failed')
    REVERSED = 'REVERSED', _('Reversed')
    REFUNDED = 'REFUNDED', _('Refunded')
    PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', _('Partially Refunded')


class RefundStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    COMPLETED = 'COMPLETED', _('Completed')
    FAILED = 'FAILED', _('Failed')
    CANCELLED = 'CANCELLED', _('Cancelled')


class MpesaTransactionStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    RECONCILED = 'RECONCILED', _('Reconciled')
    FAILED = 'FAILED', _('Failed')
    DUPLICATE = 'DUPLICATE', _('Duplicate')


class VendorPaymentTerm(models.TextChoices):
    IMMEDIATE = 'IMMEDIATE', _('Immediate')
    NET_7 = 'NET_7', _('Net 7 Days')
    NET_15 = 'NET_15', _('Net 15 Days')
    NET_30 = 'NET_30', _('Net 30 Days')
    NET_60 = 'NET_60', _('Net 60 Days')


class ExpensePaymentMethod(models.TextChoices):
    CASH = 'CASH', _('Cash')
    CHEQUE = 'CHEQUE', _('Cheque')
    BANK_TRANSFER = 'BANK_TRANSFER', _('Bank Transfer')
    MPESA = 'MPESA', _('M-Pesa')
    CARD = 'CARD', _('Card')
    PETTY_CASH = 'PETTY_CASH', _('Petty Cash')


class ExpenseStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    PENDING_APPROVAL = 'PENDING_APPROVAL', _('Pending Approval')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    PAID = 'PAID', _('Paid')
    CANCELLED = 'CANCELLED', _('Cancelled')


class ExpenseRecurrenceFrequency(models.TextChoices):
    MONTHLY = 'MONTHLY', _('Monthly')
    QUARTERLY = 'QUARTERLY', _('Quarterly')
    ANNUALLY = 'ANNUALLY', _('Annually')


class PettyCashStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', _('Active')
    SUSPENDED = 'SUSPENDED', _('Suspended')
    CLOSED = 'CLOSED', _('Closed')


class PettyCashTransactionType(models.TextChoices):
    DISBURSEMENT = 'DISBURSEMENT', _('Disbursement')
    REPLENISHMENT = 'REPLENISHMENT', _('Replenishment')
    ADJUSTMENT = 'ADJUSTMENT', _('Adjustment')


class BudgetPeriod(models.TextChoices):
    ANNUAL = 'ANNUAL', _('Annual')
    QUARTERLY = 'QUARTERLY', _('Quarterly')
    MONTHLY = 'MONTHLY', _('Monthly')


class FeeItem(GenericBaseModel):
    school = models.ForeignKey(
        School,
        null=True,
        on_delete=models.CASCADE,
        related_name='fee_items',
        verbose_name=_('School')
    )
    branches = models.ManyToManyField(
        Branch,
        blank=True,
        related_name='fee_items',
        verbose_name=_('Branches'),
        help_text=_('Leave blank to apply to all branches in the school')
    )

    default_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Default Amount')
    )
    category = models.CharField(
        max_length=50,
        choices=FeeItemCategory.choices,
        default=FeeItemCategory.OTHER,
        verbose_name=_('Category')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Fee Item')
        verbose_name_plural = _('Fee Items')
        ordering = ['school', 'category', 'name']
        unique_together = ['school', 'name']
        indexes = [
            models.Index(fields=['school']),
            models.Index(fields=['school', 'is_active']),
        ]

    def __str__(self) -> str:
        branch_info = " (All Branches)" if not self.branches.exists() else f" ({self.branches.count()} Branch(es))"
        return f'{self.name} - KES {self.default_amount}{branch_info} ({self.school.name})'

    def applies_to_all_branches(self) -> bool:
        return not self.branches.exists()


class GradeLevelFee(BaseModel):
    fee_item = models.ForeignKey(FeeItem, on_delete=models.CASCADE, verbose_name=_('Fee Item'))
    grade_level = models.CharField(max_length=10, choices=GradeLevel.choices, verbose_name=_('Grade Level'))
    term = models.CharField(max_length=20, choices=Term.choices, verbose_name=_('Term'))
    academic_year = models.CharField(max_length=9, verbose_name=_('Academic Year'))
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Amount')
    )
    is_mandatory = models.BooleanField(default=True, verbose_name=_('Is Mandatory'))

    class Meta:
        verbose_name = _('Grade Level Fee')
        verbose_name_plural = _('Grade Level Fees')
        unique_together = ['fee_item', 'grade_level', 'term', 'academic_year']
        ordering = ['grade_level', 'term']

    def __str__(self) -> str:
        return f'{self.fee_item.name} - {self.grade_level} {self.term}'


class Invoice(BaseModel):
    invoice_reference = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name=_('Invoice Reference')
    )
    student = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Student'))
    priority = models.IntegerField(
        default=1,
        help_text=_('Lower number = higher priority (1 is highest)'),
        verbose_name=_('Priority')
    )
    due_date = models.DateField(verbose_name=_('Due Date'))
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='created_invoices',
        verbose_name=_('Created By')
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='updated_invoices',
        null=True,
        blank=True,
        verbose_name=_('Updated By')
    )
    notes = models.TextField(null=True, blank=True, verbose_name=_('Notes'))
    is_auto_generated = models.BooleanField(default=False, verbose_name=_('Is Auto Generated'))
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.PENDING,
        db_index=True,
        verbose_name=_('Status')
    )

    class Meta:
        verbose_name = _('Invoice')
        verbose_name_plural = _('Invoices')
        ordering = ['priority', '-created_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self) -> str:
        return f'Invoice {self.id} - {self.student.full_name}'

    @staticmethod
    def generate_invoice_reference() -> str:
        today_str = timezone.now().strftime('%Y%m%d')
        last_invoice = Invoice.objects.filter(
            invoice_reference__startswith=f'INV-{today_str}'
        ).order_by('created_at').last()
        if last_invoice:
            last_seq = int(last_invoice.invoice_reference.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        return f'INV-{today_str}-{new_seq:04d}'

    @property
    def total_amount(self) -> Decimal:
        return Decimal(
            self.items.filter(
                is_active=True
            ).aggregate(
                total=Sum('amount')
             )['total'] or '0.00'
        )

    total_amount.fget.short_description = _('Total Amount')

    @property
    def paid_amount(self) -> Decimal:
        allocations = self.payment_allocations.filter(is_active=True)
        total_allocated = allocations.aggregate(total=Sum('allocated_amount'))['total'] or 0

        payments = Payment.objects.filter(allocations__in=allocations).distinct()
        refunded = sum(p.completed_refunded_amount for p in payments)

        return Decimal(total_allocated - refunded)

    paid_amount.fget.short_description = _('Paid Amount')

    @property
    def balance(self) -> Decimal:
        return Decimal(self.total_amount - self.paid_amount)

    balance.fget.short_description = _('Balance')

    @property
    def computed_status(self) -> str:
        if self.status == InvoiceStatus.CANCELLED:
            return InvoiceStatus.CANCELLED

        paid = self.paid_amount

        if paid == 0:
            temp_status = InvoiceStatus.PENDING
        elif paid >= self.total_amount:
            temp_status = InvoiceStatus.PAID
        else:
            temp_status = InvoiceStatus.PARTIALLY_PAID

        try:
            due_date_obj = self.due_date
            if isinstance(due_date_obj, str):
                from datetime import datetime
                due_date_obj = datetime.strptime(due_date_obj, '%Y-%m-%d').date()

            if temp_status != InvoiceStatus.PAID and timezone.now().date() > due_date_obj:
                temp_status = InvoiceStatus.OVERDUE
        except (TypeError, ValueError):
            pass

        return temp_status

    def update_status(self) -> None:
        self.status = self.computed_status
        self.save(update_fields=['status'])

    def save(self, *args, **kwargs) -> None:
        if not self.invoice_reference:
            self.invoice_reference = self.generate_invoice_reference()
        if self.status != InvoiceStatus.CANCELLED:
            self.status = self.computed_status
        super().save(*args, **kwargs)


class InvoiceItem(BaseModel):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('Invoice')
    )
    fee_item = models.ForeignKey(
        FeeItem,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name=_('Fee Item')
    )
    description = models.CharField(max_length=100, blank=True, verbose_name=_('Description'))
    quantity = models.PositiveIntegerField(default=1, verbose_name=_('Quantity'))
    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Unit Price')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Amount')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Invoice Item')
        verbose_name_plural = _('Invoice Items')
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.invoice.invoice_reference} - {self.description}'

    def save(self, *args, **kwargs) -> None:
        self.amount = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class BulkInvoice(BaseModel):
    bulk_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_('Bulk Reference')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='bulk_invoices',
        verbose_name=_('Created By')
    )

    description = models.CharField(
        max_length=255,
        blank=True,
        verbose_name=_('Description'),
        help_text=_(
            'A short description or title for this bulk invoice (e.g., "Term 1 2025 Fees", "Transport Fees Q4")')
    )

    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    student_count = models.PositiveIntegerField(verbose_name=_('Number of Students'))
    invoice_count = models.PositiveIntegerField(verbose_name=_('Number of Invoices Created'))
    total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        verbose_name=_('Total Amount Invoiced')
    )
    due_date = models.DateField(verbose_name=_('Common Due Date'))
    priority = models.IntegerField(default=1, verbose_name=_('Priority'))
    is_auto_generated = models.BooleanField(default=True, verbose_name=_('Auto Generated'))

    is_cancelled = models.BooleanField(default=False, verbose_name=_('Is Cancelled'), db_index=True)
    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cancelled_bulk_invoices',
        verbose_name=_('Cancelled By')
    )
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Cancelled At'))
    cancellation_reason = models.TextField(blank=True, verbose_name=_('Cancellation Reason'))

    invoices = models.ManyToManyField(
        Invoice,
        related_name='bulk_invoices',
        verbose_name=_('Invoices')
    )

    class Meta:
        verbose_name = _('Bulk Invoice')
        verbose_name_plural = _('Bulk Invoices')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by']),
            models.Index(fields=['due_date']),
            models.Index(fields=['bulk_reference']),
            models.Index(fields=['is_cancelled']),
        ]

    def __str__(self) -> str:
        status = " (Cancelled)" if self.is_cancelled else ""
        desc = f" - {self.description}" if self.description else ""
        return f'Bulk {self.bulk_reference}{desc} - {self.student_count} students{status}'

    @staticmethod
    def generate_bulk_reference() -> str:
        today_str = timezone.now().strftime('%Y%m%d')
        last_bulk = BulkInvoice.objects.filter(
            bulk_reference__startswith=f'BULK-{today_str}'
        ).order_by('created_at').last()
        if last_bulk:
            last_seq = int(last_bulk.bulk_reference.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        return f'BULK-{today_str}-{new_seq:04d}'

    @transaction.atomic
    def cancel(self, cancelled_by: User, reason: str = '') -> None:
        if self.is_cancelled:
            raise ValidationError(_("This bulk invoice has already been cancelled."))

        for invoice in self.invoices.select_related('student').all():
            PaymentAllocation.objects.filter(
                invoice=invoice,
                is_active=True
            ).update(is_active=False)

            invoice.status = InvoiceStatus.CANCELLED
            invoice.updated_by = cancelled_by
            invoice.save(update_fields=['status', 'updated_by'])

        self.is_cancelled = True
        self.cancelled_by = cancelled_by
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason or "Bulk invoice cancelled"
        self.save(update_fields=['is_cancelled', 'cancelled_by', 'cancelled_at', 'cancellation_reason'])


class Payment(BaseModel):
    payment_reference = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name=_('Payment Reference')
    )
    student = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)
    payment_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name=_('Payment Method')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Amount')
    )

    mpesa_receipt_number = models.CharField(max_length=100, blank=True, verbose_name=_('M-Pesa Receipt Number'))
    mpesa_phone_number = models.CharField(max_length=15, blank=True, verbose_name=_('M-Pesa Phone Number'))
    mpesa_transaction_date = models.DateTimeField(null=True, blank=True, verbose_name=_('M-Pesa Transaction Date'))

    bank_reference = models.CharField(max_length=100, blank=True, verbose_name=_('Bank Reference'))
    bank_name = models.CharField(max_length=100, blank=True, verbose_name=_('Bank Name'))

    transaction_id = models.CharField(max_length=100, blank=True, db_index=True, verbose_name=_('Transaction ID'))

    verified_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Verified At'))
    verified_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='verified_payments',
        verbose_name=_('Verified By')
    )

    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Metadata'))

    priority_invoice = models.ForeignKey(
        Invoice,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_('Priority Invoice')
    )

    status = models.CharField(
        max_length=30,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
        verbose_name=_('Status')
    )

    reversal_reason = models.TextField(blank=True, verbose_name=_('Reversal Reason'))
    reversed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='reversed_payments',
        verbose_name=_('Reversed By')
    )
    reversed_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Reversed At'))

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_method', 'status']),
        ]

    def __str__(self) -> str:
        return f'Payment {self.payment_reference} - KES {self.amount}'

    def clean(self):
        super().clean()
        if self.payment_method == PaymentMethod.MPESA and self.mpesa_receipt_number:
            if Payment.objects.filter(
                payment_method=PaymentMethod.MPESA,
                mpesa_receipt_number=self.mpesa_receipt_number
            ).exclude(pk=self.pk).exists():
                raise ValidationError({
                    'mpesa_receipt_number': _('An M-Pesa payment with this receipt number already exists.')
                })

        if self.payment_method == PaymentMethod.BANK and self.bank_reference:
            if Payment.objects.filter(
                payment_method=PaymentMethod.BANK,
                bank_reference=self.bank_reference
            ).exclude(pk=self.pk).exists():
                raise ValidationError({
                    'bank_reference': _('A bank payment with this reference already exists.')
                })

    @staticmethod
    def generate_payment_reference() -> str:
        today_str = timezone.now().strftime('%Y%m%d')
        last_payment = Payment.objects.filter(
            payment_reference__startswith=f'PAY-{today_str}'
        ).order_by('created_at').last()
        if last_payment:
            last_seq = int(last_payment.payment_reference.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        return f'PAY-{today_str}-{new_seq:04d}'

    @property
    def allocated_amount(self) -> Decimal:
        return Decimal(
            self.allocations.filter(is_active=True).aggregate(total=Sum('allocated_amount'))['total'] or 0
        )

    allocated_amount.fget.short_description = _('Allocated Amount')

    @property
    def completed_refunded_amount(self) -> Decimal:
        return Decimal(
            self.refunds.filter(status='COMPLETED').aggregate(total=Sum('amount'))['total'] or 0
        )

    completed_refunded_amount.fget.short_description = _('Completed Refunded Amount')

    @property
    def pending_refunded_amount(self) -> Decimal:
        return Decimal(
            self.refunds.filter(status='PENDING').aggregate(total=Sum('amount'))['total'] or 0
        )

    pending_refunded_amount.fget.short_description = _('Pending Refunded Amount')

    @property
    def effective_utilized_amount(self) -> Decimal:
        return max(Decimal("0.00"), (self.allocated_amount + self.completed_refunded_amount))

    effective_utilized_amount.fget.short_description = _('Effective Utilized Amount')

    @property
    def unassigned_amount(self) -> Decimal:
        return Decimal(Decimal(self.amount) - self.allocated_amount - self.completed_refunded_amount)

    unassigned_amount.fget.short_description = _('Unassigned Amount')

    @property
    def get_available_refund_amount(self) -> Decimal:
        if self.status in [PaymentStatus.PENDING, PaymentStatus.FAILED, PaymentStatus.REVERSED]:
            return Decimal("0.00")
        return Decimal(str(max(Decimal("0.00"), (self.amount - self.allocated_amount - self.completed_refunded_amount))))

    get_available_refund_amount.fget.short_description = _('Available for Refund')

    def reverse_payment(self, reversed_by: User, reason: str = '') -> None:
        if not self.status in [PaymentStatus.PENDING, PaymentStatus.COMPLETED]:
            raise ValueError(_('Only COMPLETED payments can be reversed.'))

        with transaction.atomic():
            self.allocations.filter(is_active=True).update(is_active=False)
            self.status = PaymentStatus.REVERSED
            self.reversal_reason = reason or "Payment reversed"
            self.reversed_by = reversed_by
            self.reversed_at = timezone.now()
            self.save()

            for alloc in self.allocations.all():
                alloc.invoice.save()

    def create_refund(
        self,
        amount: Decimal,
        refund_method: str,
        processed_by: User,
        notes: str = '',
        reference: str = '',
        mpesa_receipt_number: str = '',
        mpesa_phone_number: str = '',
        bank_reference: str = '',
        bank_name: str = '',
        status: str = RefundStatus.COMPLETED,
        **extra_fields
    ) -> 'Refund':
        amount = Decimal(amount).quantize(Decimal('0.01'))
        available = self.get_available_refund_amount

        if amount > available:
            raise ValueError(f"Cannot refund {amount}: only {available} available")

        if self.status not in (PaymentStatus.COMPLETED, PaymentStatus.PARTIALLY_REFUNDED):
            raise ValueError("Can only refund COMPLETED or PARTIALLY_REFUNDED payments")

        refund = Refund.objects.create(
            original_payment=self,
            amount=amount,
            refund_method=refund_method,
            notes=notes or f"Refund of KES {amount}",
            reference=reference,
            mpesa_receipt_number=mpesa_receipt_number,
            mpesa_phone_number=mpesa_phone_number,
            bank_reference=bank_reference,
            bank_name=bank_name,
            processed_by=processed_by,
            status=status,
            **extra_fields
        )

        if status == 'COMPLETED':
            all_refunded = Decimal(str(self.completed_refunded_amount)) + amount

            if all_refunded >= self.amount:
                self.status = PaymentStatus.REFUNDED
                self.allocations.filter(is_active=True).update(is_active=False)
                for alloc in self.allocations.all():
                    alloc.invoice.save()
            elif all_refunded > 0:
                self.status = PaymentStatus.PARTIALLY_REFUNDED

            self.save(update_fields=['status'])

        return refund

    def save(self, *args, **kwargs) -> None:
        if not self.payment_reference:
            self.payment_reference = self.generate_payment_reference()

        if self.status in (PaymentStatus.REVERSED, PaymentStatus.REFUNDED):
            self.allocations.filter(is_active=True).update(is_active=False)

        super().save(*args, **kwargs)


class Refund(BaseModel):
    original_payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='refunds',
        verbose_name=_('Original Payment')
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Refund Amount')
    )

    refund_method = models.CharField(
        max_length=20,
        choices=PaymentMethod.choices,
        verbose_name=_('Refund Method')
    )

    mpesa_receipt_number = models.CharField(max_length=100, blank=True, verbose_name=_('M-Pesa Receipt Number'))
    mpesa_phone_number = models.CharField(max_length=15, blank=True, verbose_name=_('M-Pesa Phone Number'))
    mpesa_transaction_date = models.DateTimeField(null=True, blank=True, verbose_name=_('M-Pesa Transaction Date'))

    bank_reference = models.CharField(max_length=100, blank=True, verbose_name=_('Bank Reference'))
    bank_name = models.CharField(max_length=100, blank=True, verbose_name=_('Bank Name'))

    transaction_id = models.CharField(max_length=100, blank=True, db_index=True, verbose_name=_('Transaction ID'))
    reference = models.CharField(max_length=100, blank=True, verbose_name=_('General Reference'))

    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    processed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        verbose_name=_('Processed By')
    )

    processed_at = models.DateTimeField(default=timezone.now, verbose_name=_('Processed At'))

    cancelled_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cancelled_refunds',
        verbose_name=_('Cancelled By')
    )
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Cancelled At'))
    cancellation_reason = models.TextField(blank=True, verbose_name=_('Cancellation Reason'))

    status = models.CharField(
        max_length=20,
        choices=RefundStatus.choices,
        default=RefundStatus.PENDING,
        db_index=True,
        verbose_name=_('Status')
    )

    class Meta:
        verbose_name = _('Refund')
        verbose_name_plural = _('Refunds')
        ordering = ['-processed_at', '-created_at']
        indexes = [
            models.Index(fields=['original_payment']),
            models.Index(fields=['refund_method', 'status']),
        ]

    def clean(self):
        super().clean()
        if self.refund_method == PaymentMethod.MPESA and self.mpesa_receipt_number:
            if Refund.objects.filter(
                refund_method=PaymentMethod.MPESA,
                mpesa_receipt_number=self.mpesa_receipt_number
            ).exclude(pk=self.pk).exists():
                raise ValidationError({
                    'mpesa_receipt_number': _('An M-Pesa refund with this receipt number already exists.')
                })

        if self.refund_method == PaymentMethod.BANK and self.bank_reference:
            if Refund.objects.filter(
                refund_method=PaymentMethod.BANK,
                bank_reference=self.bank_reference
            ).exclude(pk=self.pk).exists():
                raise ValidationError({
                    'bank_reference': _('A bank refund with this reference already exists.')
                })

    def __str__(self) -> str:
        return f'Refund KES {self.amount} ({self.get_refund_method_display()}) - {self.original_payment.payment_reference}'

    def cancel_refund(self, cancelled_by: User, reason: str = '') -> None:
        # if self.status != RefundStatus.PENDING:
        #     raise ValueError(_('Only PENDING refunds can be cancelled.'))

        with transaction.atomic():
            self.status = RefundStatus.CANCELLED
            self.cancelled_by = cancelled_by
            self.cancelled_at = timezone.now()
            self.cancellation_reason = reason or "Refund cancelled"
            self.save(update_fields=['status', 'cancelled_by', 'cancelled_at', 'cancellation_reason'])

            original_payment = self.original_payment
            if original_payment.status == PaymentStatus.PARTIALLY_REFUNDED:
                if not original_payment.refunds.filter(status=RefundStatus.COMPLETED).exists():
                    original_payment.status = PaymentStatus.COMPLETED
                    original_payment.save(update_fields=['status'])

    @property
    def student(self):
        return self.original_payment.student


class MpesaTransaction(BaseModel):
    transaction_type = models.CharField(max_length=50, verbose_name=_('Transaction Type'))
    trans_id = models.CharField(max_length=100, unique=True, db_index=True, verbose_name=_('Transaction ID'))
    trans_time = models.CharField(max_length=50, verbose_name=_('Transaction Time'))
    trans_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Transaction Amount'))
    business_short_code = models.CharField(max_length=20, verbose_name=_('Business Short Code'))
    bill_ref_number = models.CharField(max_length=50, db_index=True, verbose_name=_('Bill Reference Number'))
    msisdn = models.CharField(max_length=15, verbose_name=_('Phone Number'))
    first_name = models.CharField(max_length=100, verbose_name=_('First Name'))
    middle_name = models.CharField(max_length=100, blank=True, verbose_name=_('Middle Name'))
    last_name = models.CharField(max_length=100, blank=True, verbose_name=_('Last Name'))

    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='mpesa_transaction',
        verbose_name=_('Payment')
    )

    is_reconciled = models.BooleanField(default=False, verbose_name=_('Is Reconciled'))
    reconciliation_notes = models.TextField(blank=True, verbose_name=_('Reconciliation Notes'))

    raw_data = models.JSONField(verbose_name=_('Raw Data'))

    status = models.CharField(
        max_length=20,
        choices=MpesaTransactionStatus.choices,
        default=MpesaTransactionStatus.PENDING,
        db_index=True,
        verbose_name=_('Status')
    )

    class Meta:
        verbose_name = _('M-Pesa Transaction')
        verbose_name_plural = _('M-Pesa Transactions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bill_ref_number', 'is_reconciled']),
            models.Index(fields=['trans_id']),
        ]

    def __str__(self) -> str:
        return f'M-Pesa {self.trans_id} - KES {self.trans_amount}'


class PaymentAllocation(BaseModel):
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name=_('Payment')
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name='payment_allocations',
        verbose_name=_('Invoice')
    )
    allocated_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Allocated Amount')
    )
    allocation_order = models.PositiveIntegerField(verbose_name=_('Allocation Order'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        verbose_name = _('Payment Allocation')
        verbose_name_plural = _('Payment Allocations')
        ordering = ['created_at']

    def __str__(self) -> str:
        return f'{self.payment.payment_reference} -> {self.invoice.invoice_reference}'


class ExpenseCategory(GenericBaseModel):
    school = models.ForeignKey(School, null=True, on_delete=models.CASCADE, verbose_name=_('School'))
    name = models.CharField(max_length=100, verbose_name=_('Category Name'))
    has_budget = models.BooleanField(default=False, verbose_name=_('Has Budget'))
    monthly_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Monthly Budget')
    )
    annual_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Annual Budget')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    requires_approval = models.BooleanField(default=False, verbose_name=_('Requires Approval'))

    class Meta:
        verbose_name = _('Expense Category')
        verbose_name_plural = _('Expense Categories')
        ordering = ['name']

    def __str__(self) -> str:
        return self.name

    def get_total_spent(self, start_date=None, end_date=None) -> Decimal:
        expenses = self.expenses.filter(status=ExpenseStatus.PAID)
        if start_date:
            expenses = expenses.filter(expense_date__gte=start_date)
        if end_date:
            expenses = expenses.filter(expense_date__lte=end_date)

        total = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        return Decimal(total)


class Vendor(BaseModel):
    name = models.CharField(max_length=100, unique=True, verbose_name=_('Vendor Name'))
    school = models.ForeignKey(School, null=True, on_delete=models.CASCADE, verbose_name=_('School'))
    contact_person = models.CharField(max_length=100, blank=True, verbose_name=_('Contact Person'))
    email = models.EmailField(blank=True, verbose_name=_('Email Address'))
    phone = models.CharField(max_length=20, blank=True, verbose_name=_('Phone Number'))
    address = models.TextField(blank=True, verbose_name=_('Address'))
    kra_pin = models.CharField(max_length=50, blank=True, verbose_name=_('KRA PIN'))
    payment_terms = models.CharField(
        max_length=20,
        choices=VendorPaymentTerm.choices,
        default=VendorPaymentTerm.NET_30,
        verbose_name=_('Payment Terms')
    )
    mpesa_pochi_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Pochi la Biashara phone number'),
        verbose_name=_('MPESA Pochi Number')
    )
    mpesa_paybill_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Paybill business number'),
        verbose_name=_('MPESA Paybill Number')
    )
    mpesa_paybill_account = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Account number to use with Paybill'),
        verbose_name=_('MPESA Paybill Account')
    )
    mpesa_till_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Buy Goods Till number'),
        verbose_name=_('MPESA Till Number')
    )
    bank_name = models.CharField(max_length=100, blank=True, verbose_name=_('Bank Name'))
    bank_account = models.CharField(max_length=50, blank=True, verbose_name=_('Bank Account Number'))
    bank_branch = models.CharField(max_length=100, blank=True, verbose_name=_('Bank Branch'))
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        ordering = ['name']
        verbose_name = _('Vendor')
        verbose_name_plural = _('Vendors')

    def __str__(self) -> str:
        return self.name

    def get_total_paid(self, year=None) -> Decimal:
        expenses = self.expenses.filter(status='APPROVED')
        if year:
            expenses = expenses.filter(expense_date__year=year)
        return Decimal(expenses.aggregate(Sum('amount'))['amount__sum'] or 0)


class Department(GenericBaseModel):
    name = models.CharField(max_length=100, verbose_name=_('Department Name'))
    school = models.ForeignKey(School, null=True, on_delete=models.CASCADE, verbose_name=_('School'))
    head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments',
        verbose_name=_('Department Head')
    )
    budget_allocated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Budget Allocated')
    )
    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        ordering = ['name']
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')

    def __str__(self) -> str:
        return self.name

    def get_total_expenses(self, start_date=None, end_date=None) -> Decimal:
        expenses = self.expenses.filter(status='APPROVED')
        if start_date:
            expenses = expenses.filter(expense_date__gte=start_date)
        if end_date:
            expenses = expenses.filter(expense_date__lte=end_date)
        return Decimal(expenses.aggregate(Sum('amount'))['amount__sum'] or 0)

    def get_budget_utilization(self) -> int:
        if self.budget_allocated > 0:
            spent = self.get_total_expenses(start_date=timezone.now().replace(month=1, day=1).date())
            return round((spent / Decimal(self.budget_allocated)) * 100)
        return 0


class Expense(GenericBaseModel):
    expense_reference = models.CharField(
        max_length=50,
        unique=True,
        db_index=True,
        verbose_name=_('Expense Reference')
    )
    school = models.ForeignKey(
        School,
        null=True,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name=_('School')
    )
    branches = models.ManyToManyField(
        Branch,
        blank=True,
        related_name='expenses',
        verbose_name=_('Branches'),
        help_text=_('Leave blank for school-level expense (applies to all branches)')
    )
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name=_('Category')
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='expenses',
        verbose_name=_('Department')
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name='expenses',
        null=True,
        blank=True,
        verbose_name=_('Vendor')
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Amount')
    )

    expense_date = models.DateField(
        default=timezone.now,
        verbose_name=_('Expense Date')
    )

    payment_method = models.CharField(
        max_length=20,
        choices=ExpensePaymentMethod.choices,
        verbose_name=_('Payment Method')
    )

    status = models.CharField(
        max_length=20,
        choices=ExpenseStatus.choices,
        default=ExpenseStatus.DRAFT,
        db_index=True,
        verbose_name=_('Status')
    )

    invoice_number = models.CharField(max_length=100, blank=True, verbose_name=_('Invoice Number'))
    receipt_number = models.CharField(max_length=100, blank=True, verbose_name=_('Receipt Number'))
    cheque_number = models.CharField(max_length=50, blank=True, verbose_name=_('Cheque Number'))
    transaction_reference = models.CharField(max_length=100, blank=True, verbose_name=_('Transaction Reference'))

    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='requested_expenses',
        verbose_name=_('Requested By')
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approved_expenses',
        verbose_name=_('Approved By')
    )
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='rejected_expenses',
        verbose_name=_('Rejected By')
    )

    approved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Approved At'))
    rejected_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Rejected At'))
    rejection_reason = models.TextField(blank=True, verbose_name=_('Rejection Reason'))

    paid_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Paid At'))
    paid_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='paid_expenses',
        verbose_name=_('Paid By')
    )

    is_taxable = models.BooleanField(default=False, verbose_name=_('Is Taxable'))
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax Rate')
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Tax Amount')
    )

    is_recurring = models.BooleanField(default=False, verbose_name=_('Is Recurring'))
    recurrence_frequency = models.CharField(
        max_length=20,
        choices=ExpenseRecurrenceFrequency.choices,
        blank=True,
        null=True,
        verbose_name=_('Recurrence Frequency')
    )

    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['expense_date', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['vendor']),
        ]
        verbose_name = _('Expense')
        verbose_name_plural = _('Expenses')

    def __str__(self) -> str:
        return f'{self.expense_reference} - {self.name}'

    def save(self, *args, **kwargs) -> None:
        if not self.expense_reference:
            self.expense_reference = self.generate_expense_reference()

        if self.is_taxable:
            self.tax_amount = self.amount * (self.tax_rate / 100)
        else:
            self.tax_amount = Decimal('0.00')

        super().save(*args, **kwargs)

    @staticmethod
    def generate_expense_reference() -> str:
        today_str = timezone.now().strftime('%Y%m%d')
        last_expense = Expense.objects.filter(
            expense_reference__startswith=f'EXP-{today_str}'
        ).order_by('created_at').last()
        if last_expense:
            last_seq = int(last_expense.expense_reference.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        return f'EXP-{today_str}-{new_seq:04d}'

    @property
    def total_amount(self) -> Decimal:
        return Decimal(self.amount + self.tax_amount if self.tax_amount else self.amount)

    def can_edit(self, user) -> bool:
        if self.status in [ExpenseStatus.PAID, ExpenseStatus.CANCELLED]:
            return False

        if user == self.requested_by and self.status == ExpenseStatus.DRAFT:
            return True

        return user.role.name == RoleName.ADMIN or user.is_superuser


class ExpenseAttachment(GenericBaseModel):
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='attachments',
        verbose_name=_('Expense')
    )
    file = models.FileField(
        upload_to='expenses/attachments/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
            )
        ],
        verbose_name=_('File')
    )
    file_name = models.CharField(max_length=255, verbose_name=_('File Name'))
    file_type = models.CharField(max_length=50, verbose_name=_('File Type'))
    file_size = models.IntegerField(help_text=_('Size in bytes'), verbose_name=_('File Size'))

    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Uploaded By'))

    is_active = models.BooleanField(default=True, verbose_name=_('Is Active'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Expense Attachment')
        verbose_name_plural = _('Expense Attachments')

    def __str__(self) -> str:
        return f'{self.file_name} - {self.expense.expense_reference}'

    def save(self, *args, **kwargs) -> None:
        if self.file:
            self.file_name = self.file.name
            self.file_size = self.file.size
            self.file_type = self.file.name.split('.')[-1].upper()
        super().save(*args, **kwargs)


class PettyCash(BaseModel):
    school = models.ForeignKey(School, null=True, on_delete=models.CASCADE, verbose_name=_('School'))
    fund_name = models.CharField(max_length=100, verbose_name=_('Fund Name'))
    custodian = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='petty_cash_funds',
        verbose_name=_('Custodian')
    )
    initial_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Initial Amount')
    )
    current_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Current Balance')
    )
    status = models.CharField(
        max_length=20,
        choices=PettyCashStatus.choices,
        default=PettyCashStatus.ACTIVE,
        verbose_name=_('Status')
    )

    class Meta:
        verbose_name = _('Petty Cash Fund')
        verbose_name_plural = _('Petty Cash Funds')

    def __str__(self) -> str:
        return f'{self.fund_name} - KES {self.current_balance}'

    def replenish(self, amount, replenished_by, notes='') -> None:
        last_transaction = PettyCashTransaction.objects.filter(petty_cash_fund=self).order_by('-created_at').first()
        balance_before = last_transaction.balance_after if last_transaction else self.current_balance
        balance_after = Decimal(balance_before + Decimal(amount))
        PettyCashTransaction.objects.create(
            petty_cash_fund=self,
            transaction_type=PettyCashTransactionType.REPLENISHMENT,
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            processed_by=replenished_by,
            notes=notes
        )
        self.current_balance += amount
        self.save()

    def disburse(self, expense, disbursed_by, notes='') -> None:
        last_transaction = PettyCashTransaction.objects.filter(petty_cash_fund=self).order_by('-created_at').first()
        balance_before = last_transaction.balance_after if last_transaction else self.current_balance
        balance_after = Decimal(balance_before - Decimal(expense.amount))
        PettyCashTransaction.objects.create(
            petty_cash_fund=self,
            transaction_type=PettyCashTransactionType.DISBURSEMENT,
            amount=expense.amount,
            balance_before=balance_before,
            balance_after=balance_after,
            processed_by=disbursed_by,
            description=f'Payment for {expense.expense_reference} - {expense.name}',
            notes=notes
        )
        self.current_balance -= expense.amount
        self.save()


class PettyCashTransaction(BaseModel):
    petty_cash_fund = models.ForeignKey(
        PettyCash,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name=_('Petty Cash Fund')
    )
    description = models.TextField(verbose_name=_('Description'))
    transaction_type = models.CharField(
        max_length=20,
        choices=PettyCashTransactionType.choices,
        verbose_name=_('Transaction Type')
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Amount')
    )
    expense = models.OneToOneField(
        Expense,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='petty_cash_transaction',
        verbose_name=_('Expense')
    )
    processed_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Processed By'))
    balance_before = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Balance Before'))
    balance_after = models.DecimalField(max_digits=10, decimal_places=2, verbose_name=_('Balance After'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Petty Cash Transaction')
        verbose_name_plural = _('Petty Cash Transactions')

    def __str__(self) -> str:
        return f'{self.transaction_type} - KES {self.amount}'

    def save(self, *args, **kwargs) -> None:
        if not self.pk:
            self.balance_before = self.petty_cash_fund.current_balance
            if self.transaction_type == PettyCashTransactionType.DISBURSEMENT:
                self.balance_after = self.balance_before - self.amount
            else:
                self.balance_after = self.balance_before + self.amount

            self.petty_cash_fund.current_balance = self.balance_after
            self.petty_cash_fund.save()

        super().save(*args, **kwargs)


class ExpenseBudget(BaseModel):
    fiscal_year = models.CharField(max_length=9, verbose_name=_('Fiscal Year'))
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.CASCADE,
        related_name='budgets',
        verbose_name=_('Category')
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='budgets',
        null=True,
        blank=True,
        verbose_name=_('Department')
    )
    budget_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name=_('Budget Amount')
    )
    period = models.CharField(
        max_length=20,
        choices=BudgetPeriod.choices,
        default=BudgetPeriod.ANNUAL,
        verbose_name=_('Budget Period')
    )
    start_date = models.DateField(verbose_name=_('Start Date'))
    end_date = models.DateField(verbose_name=_('End Date'))
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    created_by = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Created By'))

    class Meta:
        unique_together = ['fiscal_year', 'category', 'department', 'period']
        ordering = ['-fiscal_year', 'category']
        verbose_name = _('Expense Budget')
        verbose_name_plural = _('Expense Budgets')

    def __str__(self) -> str:
        dept = f' - {self.department.name}' if self.department else ''
        return f'{self.fiscal_year} - {self.category.name}{dept}'

    def get_spent_amount(self) -> Decimal:
        expenses = Expense.objects.filter(
            category=self.category,
            status=ExpenseStatus.APPROVED,
            expense_date__gte=self.start_date,
            expense_date__lte=self.end_date
        )
        if self.department:
            expenses = expenses.filter(department=self.department)
        return Decimal(expenses.aggregate(Sum('amount'))['amount__sum'] or 0)

    def get_utilization_percentage(self) -> Decimal:
        spent = self.get_spent_amount()
        percentage = (spent / Decimal(self.budget_amount) * 100) if self.budget_amount > 0 else 0
        return Decimal(round(percentage, 2))

    def get_remaining_budget(self) -> Decimal:
        return Decimal(self.budget_amount - self.get_spent_amount())


class BalanceSheet(BaseModel):
    date = models.DateField(unique=True, db_index=True, verbose_name=_('Date'))

    total_invoiced = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Invoiced')
    )
    total_collected = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Collected')
    )
    total_outstanding = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Outstanding')
    )
    total_overdue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Total Overdue')
    )

    mpesa_collections = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('M-Pesa Collections')
    )
    bank_collections = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Bank Collections')
    )
    cash_collections = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_('Cash Collections')
    )

    number_of_invoices = models.IntegerField(default=0, verbose_name=_('Number of Invoices'))
    number_of_payments = models.IntegerField(default=0, verbose_name=_('Number of Payments'))
    number_of_paid_invoices = models.IntegerField(default=0, verbose_name=_('Number of Paid Invoices'))
    number_of_pending_invoices = models.IntegerField(default=0, verbose_name=_('Number of Pending Invoices'))

    generated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_('Generated By')
    )

    metadata = models.JSONField(default=dict, blank=True, verbose_name=_('Metadata'))

    class Meta:
        ordering = ['-created_at']
        verbose_name = _('Balance Sheet')
        verbose_name_plural = _('Balance Sheets')

    def __str__(self) -> str:
        return f'Balance Sheet - {self.date}'
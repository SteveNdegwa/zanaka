from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel, GenericBaseModel
from schools.models import GradeLevel
from users.models import User


class FeeItemCategory(models.TextChoices):
    TUITION = 'tuition', _('Tuition Fees')
    TRANSPORT = 'transport', _('Transport Fees')
    ACTIVITY = 'activity', _('Activity Fees')
    UNIFORM = 'uniform', _('Uniform')
    OTHER = 'other', _('Other')


class Term(models.TextChoices):
    TERM_1 = 'term_1', _('Term 1')
    TERM_2 = 'term_2', _('Term 2')
    TERM_3 = 'term_3', _('Term 3')


class InvoiceStatus(models.TextChoices):
    DRAFT = 'draft', _('Draft')
    PENDING = 'pending', _('Pending')
    PARTIALLY_PAID = 'partially_paid', _('Partially Paid')
    PAID = 'paid', _('Paid')
    OVERDUE = 'overdue', _('Overdue')
    CANCELLED = 'cancelled', _('Cancelled')


class PaymentMethod(models.TextChoices):
    MPESA = 'mpesa', _('M-Pesa')
    BANK = 'bank', _('Bank Transfer')
    CASH = 'cash', _('Cash')
    CHEQUE = 'cheque', _('Cheque')
    CARD = 'card', _('Card')


class PaymentStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    COMPLETED = 'completed', _('Completed')
    FAILED = 'failed', _('Failed')
    REVERSED = 'reversed', _('Reversed')


class MpesaTransactionStatus(models.TextChoices):
    PENDING = 'pending', _('Pending')
    RECONCILED = 'reconciled', _('Reconciled')
    FAILED = 'failed', _('Failed')
    DUPLICATE = 'duplicate', _('Duplicate')


class FeeItem(GenericBaseModel):
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
        ordering = ['category', 'name']

    def __str__(self):
        return f"{self.name} - KES {self.default_amount}"


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
        unique_together = ['fee_item', 'grade_level', 'term', 'academic_year']
        ordering = ['grade_level', 'term']

    def __str__(self):
        return f"{self.fee_item.name} - {self.grade_level} {self.term}"


class Invoice(BaseModel):
    invoice_reference = models.CharField(
        max_length=50,
        blank=True,
        unique=True,
        db_index=True,
        verbose_name=_('Invoice Reference')
    )
    student = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name=_('Student'))
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name=_('Total Amount')
    )
    paid_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Paid Amount')
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Balance')
    )
    priority = models.IntegerField(
        default=1,
        help_text=_("Lower number = higher priority (1 is highest)"),
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
    notes = models.TextField(blank=True, verbose_name=_('Notes'))
    is_auto_generated = models.BooleanField(default=False, verbose_name=_('Is Auto Generated'))
    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.PENDING,
        db_index=True,
        verbose_name=_('Status')
    )

    class Meta:
        ordering = ['priority', '-created_at']
        indexes = [
            models.Index(fields=['student', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['priority', 'status']),
        ]

    def __str__(self):
        return f"Invoice {self.id} - {self.student.get_full_name()}"

    @staticmethod
    def generate_invoice_reference():
        today_str = timezone.now().strftime("%Y%m%d")
        last_invoice = Invoice.objects.filter(
            invoice_reference__startswith=f"INV-{today_str}"
        ).order_by('created_at').last()
        if last_invoice:
            last_seq = int(last_invoice.invoice_reference.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        return f"INV-{today_str}-{new_seq:04d}"

    def update_status(self):
        if self.status == InvoiceStatus.CANCELLED:
            return

        if self.paid_amount == 0:
            self.status = InvoiceStatus.PENDING
        elif self.paid_amount >= self.total_amount:
            self.status = InvoiceStatus.PAID
        else:
            self.status = InvoiceStatus.PARTIALLY_PAID

        if self.status != InvoiceStatus.PAID and timezone.now().date() > self.due_date:
            self.status = InvoiceStatus.OVERDUE

    def save(self, *args, **kwargs):
        if not self.invoice_reference:
            self.invoice_reference = self.generate_invoice_reference()

        self.balance = self.total_amount - self.paid_amount
        self.update_status()

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
        ordering = ['id']

    def __str__(self):
        return f"{self.invoice.invoice_reference} - {self.fee_item.name}"


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
    utilized_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name=_('Utilized Amount')
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

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
        verbose_name=_('Status')
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_method', 'status']),
            models.Index(fields=['mpesa_receipt_number']),
        ]

    def __str__(self):
        return f"Payment {self.payment_reference} - KES {self.amount}"

    @staticmethod
    def generate_payment_reference():
        today_str = timezone.now().strftime("%Y%m%d")
        last_payment = Payment.objects.filter(
            payment_reference__startswith=f"PAY-{today_str}"
        ).order_by('created_at').last()
        if last_payment:
            last_seq = int(last_payment.payment_reference.split('-')[-1])
            new_seq = last_seq + 1
        else:
            new_seq = 1
        return f"PAY-{today_str}-{new_seq:04d}"

    def save(self, *args, **kwargs):
        if not self.payment_reference:
            self.payment_reference = self.generate_payment_reference()

        super().save(*args, **kwargs)

    @property
    def unassigned_amount(self):
        return self.amount - self.utilized_amount


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
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bill_ref_number', 'is_reconciled']),
            models.Index(fields=['trans_id']),
        ]

    def __str__(self):
        return f"M-Pesa {self.trans_id} - KES {self.trans_amount}"


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
        ordering = ['allocation_order']

    def __str__(self):
        return f"{self.payment.payment_reference} -> {self.invoice.invoice_reference}"


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
        ordering = ['-date']

    def __str__(self):
        return f"Balance Sheet - {self.date}"

from decimal import Decimal

from django.db import models
from django.core.validators import MinValueValidator, FileExtensionValidator
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from base.models import BaseModel, GenericBaseModel
from finances.managers import InvoiceManager
from schools.models import GradeLevel
from users.models import User, RoleName


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


class VendorPaymentTerms(models.TextChoices):
    IMMEDIATE = 'pending', _('Immediate')
    NET_7 = 'net_7', _('Net 7 Days')
    NET_15 = 'net_15', _('Net 15 Days')
    NET_30 = 'net_30', _('Net 30 Days')
    NET_60 = 'net_60', _('Net 60 Days')


class ExpensePaymentMethod(models.TextChoices):
    CASH = 'cash', _('Cash')
    CHEQUE = 'cheque', _('Cheque')
    BANK_TRANSFER = 'bank_transfer', _('Bank Transfer')
    MPESA = 'mpesa', _('M-Pesa')
    CARD = 'card', _('Card')
    PETTY_CASH = 'petty_cash', _('Petty Cash')


class ExpenseStatus(models.TextChoices):
    DRAFT = 'draft', _('Draft')
    PENDING_APPROVAL = 'pending_approval', _('Pending Approval')
    APPROVED = 'approved', _('Approved')
    REJECTED = 'rejected', _('Rejected')
    PAID = 'paid', _('Paid')
    CANCELLED = 'cancelled', _('Cancelled')


class ExpenseRecurrenceFrequency(models.TextChoices):
    MONTHLY = 'monthly', _('Monthly')
    QUARTERLY = 'quarterly', _('Quarterly')
    ANNUALLY = 'annually', _('Annually')


class PettyCashStatus(models.TextChoices):
    ACTIVE = 'active', _('Active')
    SUSPENDED = 'suspended', _('Suspended')
    CLOSED = 'closed', _('Closed')


class PettyCashTransactionType(models.TextChoices):
    DISBURSEMENT = 'disbursement', _('Disbursement')
    REPLENISHMENT = 'replenishment', _('Replenishment')
    ADJUSTMENT = 'adjustment', _('Adjustment')


class BudgetPeriod(models.TextChoices):
    ANNUAL = 'annual', _('Annual')
    QUARTERLY = 'quarterly', _('Quarterly')
    MONTHLY = 'monthly', _('Monthly')


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

    objects = InvoiceManager()

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

    @property
    def total_amount(self):
        return self.items.filter(
            is_active=True
        ).aggregate(
            total=Sum('amount')
        )['total'] or 0

    total_amount.fget.short_description = "Total Amount"

    @property
    def paid_amount(self):
        return self.payment_allocations.filter(
            is_active=True
        ).aggregate(
            total=Sum('allocated_amount')
        )['total'] or 0

    paid_amount.fget.short_description = "Paid Amount"

    @property
    def balance(self):
        return self.total_amount - self.paid_amount

    balance.fget.short_description = "Balance"

    @property
    def computed_status(self):
        paid = self.paid_amount

        if paid == 0:
            temp_status = InvoiceStatus.PENDING
        elif paid >= self.total_amount:
            temp_status = InvoiceStatus.PAID
        else:
            temp_status = InvoiceStatus.PARTIALLY_PAID

        if temp_status != InvoiceStatus.PAID and timezone.now().date() > self.due_date:
            temp_status = InvoiceStatus.OVERDUE

        return temp_status

    def save(self, *args, **kwargs):
        if not self.invoice_reference:
            self.invoice_reference = self.generate_invoice_reference()
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
        ordering = ['id']

    def __str__(self):
        return f"{self.invoice.invoice_reference} - {self.fee_item.name}"

    def save(self, *args, **kwargs):
        self.amount = self.unit_price * self.quantity
        super().save(*args, **kwargs)


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

    @property
    def utilized_amount(self):
        return self.allocations.filter(
            is_active=True
        ).aggregate(
            total=Sum('allocated_amount')
        )['total'] or 0

    utilized_amount.fget.short_description = "Utilized Amount"

    @property
    def unassigned_amount(self):
        return self.amount - self.utilized_amount

    unassigned_amount.fget.short_description = "Unassigned Amount"

    def save(self, *args, **kwargs):
        if not self.payment_reference:
            self.payment_reference = self.generate_payment_reference()

        if self.status != PaymentStatus.COMPLETED:
            self.allocations.filter(is_active=True).update(is_active=False)

        super().save(*args, **kwargs)


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


class ExpenseCategory(GenericBaseModel):
    name = models.CharField(max_length=100, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='subcategories'
    )

    # Budget settings
    has_budget = models.BooleanField(default=False)
    monthly_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    annual_budget = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    is_active = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Expense Categories'
        ordering = ['name']

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_full_path(self):
        path = [self.name]
        parent = self.parent
        while parent:
            path.insert(0, parent.name)
            parent = parent.parent
        return ' > '.join(path)

    def get_total_spent(self, start_date=None, end_date=None):
        expenses = self.expenses.filter(status='approved')
        if start_date:
            expenses = expenses.filter(expense_date__gte=start_date)
        if end_date:
            expenses = expenses.filter(expense_date__lte=end_date)

        from django.db.models import Sum
        total = expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        # Include subcategories
        for subcategory in self.subcategories.all():
            total += subcategory.get_total_spent(start_date, end_date)

        return total


class Vendor(GenericBaseModel):
    name = models.CharField(max_length=100, unique=True)

    contact_person = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    address = models.TextField(blank=True)
    tax_id = models.CharField(max_length=50, blank=True, verbose_name='KRA PIN')

    payment_terms = models.CharField(
        max_length=20,
        choices=VendorPaymentTerms.choices,
        default=VendorPaymentTerms.NET_30
    )

    mpesa_pochi_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Pochi la Biashara phone number"
    )

    mpesa_paybill_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Paybill business number"
    )

    mpesa_paybill_account = models.CharField(
        max_length=50,
        blank=True,
        help_text="Account number to use with Paybill"
    )

    mpesa_till_number = models.CharField(
        max_length=20,
        blank=True,
        help_text="Buy Goods Till number"
    )

    bank_name = models.CharField(max_length=100, blank=True)
    bank_account = models.CharField(max_length=50, blank=True)
    bank_branch = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_total_paid(self, year=None):
        from django.db.models import Sum
        expenses = self.expenses.filter(status='approved')
        if year:
            expenses = expenses.filter(expense_date__year=year)
        return expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')


class Department(GenericBaseModel):
    name = models.CharField(max_length=100, unique=True)
    head = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments'
    )

    budget_allocated = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00')
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_total_expenses(self, start_date=None, end_date=None):
        from django.db.models import Sum
        expenses = self.expenses.filter(status='approved')
        if start_date:
            expenses = expenses.filter(expense_date__gte=start_date)
        if end_date:
            expenses = expenses.filter(expense_date__lte=end_date)
        return expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    def get_budget_utilization(self):
        if self.budget_allocated > 0:
            spent = self.get_total_expenses(
                start_date=timezone.now().replace(month=1, day=1).date()
            )
            return (spent / self.budget_allocated) * 100
        return 0


class Expense(GenericBaseModel):
    expense_reference = models.CharField(max_length=50, unique=True, db_index=True)

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='expenses'
    )
    vendor = models.ForeignKey(
        Vendor,
        on_delete=models.PROTECT,
        related_name='expenses',
        null=True,
        blank=True
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    expense_date = models.DateField(default=timezone.now)

    payment_method = models.CharField(
        max_length=20,
        choices=ExpensePaymentMethod.choices
    )

    status = models.CharField(
        max_length=20,
        choices=ExpenseStatus.choices,
        default=ExpenseStatus.DRAFT,
        db_index=True
    )

    # Reference numbers
    invoice_number = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    cheque_number = models.CharField(max_length=50, blank=True)
    transaction_reference = models.CharField(max_length=100, blank=True)

    # Approval workflow
    requested_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='requested_expenses'
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='approved_expenses'
    )
    rejected_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='rejected_expenses'
    )

    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    paid_at = models.DateTimeField(null=True, blank=True)
    paid_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='paid_expenses'
    )

    # Tax information
    is_taxable = models.BooleanField(default=False)
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('0.00')
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    is_recurring = models.BooleanField(default=False)
    recurrence_frequency = models.CharField(
        max_length=20,
        choices=ExpenseRecurrenceFrequency.choices,
        blank=True,
        null=True
    )

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        indexes = [
            models.Index(fields=['expense_date', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['vendor']),
        ]

    def __str__(self):
        return f"{self.expense_reference} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.expense_reference:
            self.expense_reference = self.generate_expense_reference()

        # Calculate tax
        if self.is_taxable:
            self.tax_amount = self.amount * (self.tax_rate / 100)
        else:
            self.tax_amount = Decimal('0.00')

        super().save(*args, **kwargs)

    @staticmethod
    def generate_expense_reference():
        prefix = timezone.now().strftime('EXP%Y%m')
        count = Expense.objects.filter(
            expense_number__startswith=prefix
        ).count() + 1
        return f"{prefix}{count:05d}"

    @property
    def total_amount(self):
        return self.amount + self.tax_amount

    def can_edit(self, user):
        if self.status in [ExpenseStatus.PAID, ExpenseStatus.CANCELLED]:
            return False

        if user == self.requested_by and self.status == ExpenseStatus.DRAFT:
            return True

        return user.role.name == RoleName.ADMIN or user.is_superuser


class ExpenseAttachment(GenericBaseModel):
    expense = models.ForeignKey(
        Expense,
        on_delete=models.CASCADE,
        related_name='attachments'
    )

    file = models.FileField(
        upload_to='expenses/attachments/%Y/%m/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png', 'doc', 'docx', 'xls', 'xlsx']
            )
        ]
    )

    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size = models.IntegerField(help_text="Size in bytes")  # Size in bytes

    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} - {self.expense.expense_number}"

    def save(self, *args, **kwargs):
        if self.file:
            self.file_name = self.file.name
            self.file_size = self.file.size
            self.file_type = self.file.name.split('.')[-1].upper()
        super().save(*args, **kwargs)


class PettyCash(BaseModel):
    fund_name = models.CharField(max_length=100)
    custodian = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='petty_cash_funds'
    )

    initial_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    current_balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    status = models.CharField(
        max_length=20,
        choices=PettyCashStatus.choices,
        default=PettyCashStatus.ACTIVE
    )

    class Meta:
        verbose_name = 'Petty Cash Fund'
        verbose_name_plural = 'Petty Cash Funds'

    def __str__(self):
        return f"{self.fund_name} - KES {self.current_balance}"

    def replenish(self, amount, replenished_by, notes=''):
        PettyCashTransaction.objects.create(
            petty_cash_fund=self,
            transaction_type='replenishment',
            amount=amount,
            processed_by=replenished_by,
            notes=notes
        )
        self.current_balance += amount
        self.save()


class PettyCashTransaction(BaseModel):
    petty_cash_fund = models.ForeignKey(
        PettyCash,
        on_delete=models.CASCADE,
        related_name='transactions'
    )
    description = models.TextField()

    transaction_type = models.CharField(
        max_length=20,
        choices=PettyCashTransactionType.choices
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    expense = models.OneToOneField(
        Expense,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='petty_cash_transaction'
    )

    processed_by = models.ForeignKey(User, on_delete=models.PROTECT)

    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)

    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - KES {self.amount}"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.balance_before = self.petty_cash_fund.current_balance

            if self.transaction_type == 'disbursement':
                self.balance_after = self.balance_before - self.amount
            else:  # replenishment or adjustment
                self.balance_after = self.balance_before + self.amount

            self.petty_cash_fund.current_balance = self.balance_after
            self.petty_cash_fund.save()

        super().save(*args, **kwargs)


class ExpenseBudget(BaseModel):
    fiscal_year = models.CharField(max_length=9)

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.CASCADE,
        related_name='budgets'
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='budgets',
        null=True,
        blank=True
    )

    budget_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )

    period = models.CharField(
        max_length=20,
        choices=BudgetPeriod.choices,
        default=BudgetPeriod.ANNUAL
    )

    start_date = models.DateField()
    end_date = models.DateField()

    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        unique_together = ['fiscal_year', 'category', 'department', 'period']
        ordering = ['-fiscal_year', 'category']

    def __str__(self):
        dept = f" - {self.department.name}" if self.department else ""
        return f"{self.fiscal_year} - {self.category.name}{dept}"

    def get_spent_amount(self):
        expenses = Expense.objects.filter(
            category=self.category,
            status=ExpenseStatus.APPROVED,
            expense_date__gte=self.start_date,
            expense_date__lte=self.end_date
        )

        if self.department:
            expenses = expenses.filter(department=self.department)

        from django.db.models import Sum
        return expenses.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    def get_utilization_percentage(self):
        spent = self.get_spent_amount()
        return (spent / self.budget_amount * 100) if self.budget_amount > 0 else 0

    def get_remaining_budget(self):
        return self.budget_amount - self.get_spent_amount()


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

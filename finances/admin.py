from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    FeeItem,
    GradeLevelFee,
    Invoice,
    InvoiceItem,
    Payment,
    PaymentAllocation,
    Refund,
    MpesaTransaction,
    ExpenseCategory,
    Vendor,
    Department,
    Expense,
    ExpenseAttachment,
    PettyCash,
    PettyCashTransaction,
    ExpenseBudget,
    BalanceSheet, ExpenseStatus, PaymentStatus, InvoiceStatus
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1
    fields = ('fee_item', 'description', 'quantity', 'unit_price', 'amount', 'is_active')
    readonly_fields = ('amount',)


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    fields = ('invoice', 'allocated_amount', 'allocation_order', 'is_active')
    raw_id_fields = ('invoice',)


class RefundInline(admin.TabularInline):
    model = Refund
    extra = 0
    fields = (
        'amount', 'refund_method', 'status', 'processed_by', 'processed_at', 'mpesa_receipt_number',
        'bank_reference', 'cancelled_by', 'cancelled_at', 'cancellation_reason'
    )
    readonly_fields = ('processed_at',)
    can_delete = True


class ExpenseAttachmentInline(admin.TabularInline):
    model = ExpenseAttachment
    extra = 1
    fields = ('file', 'file_name', 'uploaded_by')
    readonly_fields = ('file_name', 'uploaded_by', 'file_type', 'file_size')


class PettyCashTransactionInline(admin.TabularInline):
    model = PettyCashTransaction
    extra = 0
    fields = ('transaction_type', 'amount', 'description', 'processed_by', 'balance_after')
    readonly_fields = ('balance_after',)


class GradeLevelFeeInline(admin.TabularInline):
    model = GradeLevelFee
    extra = 1
    fields = ('grade_level', 'term', 'academic_year', 'amount', 'is_mandatory')
    verbose_name = _('Grade Level Fee Override')
    verbose_name_plural = _('Grade Level Fee Overrides')


AUDIT_FIELDSET = (
    _('Audit'),
    {
        'fields': ('id', 'created_at', 'updated_at', 'synced'),
        'classes': ('collapse',),
    },
)

AUDIT_READONLY_FIELDS = ('id', 'created_at', 'updated_at', 'synced')


@admin.register(FeeItem)
class FeeItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'category', 'default_amount', 'is_active')
    list_filter = ('school', 'category', 'is_active')
    search_fields = ('name', 'school__name')
    readonly_fields = AUDIT_READONLY_FIELDS
    filter_horizontal = ('branches',)

    inlines = (GradeLevelFeeInline,)

    fieldsets = (
        (_('School Assignment'), {
            'fields': ('school', 'branches'),
            'description': _('Required: Select the school. Optional: Limit to specific branches (leave empty for all).'),
        }),
        (_('Fee Item Details'), {
            'fields': ('name', 'category', 'description', 'default_amount', 'is_active')
        }),
        AUDIT_FIELDSET,
    )


@admin.register(GradeLevelFee)
class GradeLevelFeeAdmin(admin.ModelAdmin):
    list_display = ('fee_item', 'grade_level', 'term', 'academic_year', 'amount', 'is_mandatory')
    list_filter = ('academic_year', 'term', 'grade_level', 'is_mandatory')
    search_fields = ('fee_item__name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Fee Assignment'), {
            'fields': ('fee_item', 'grade_level', 'term', 'academic_year')
        }),
        (_('Amount & Rules'), {
            'fields': ('amount', 'is_mandatory')
        }),
        AUDIT_FIELDSET,
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_reference',
        'student',
        'total_amount',
        'paid_amount',
        'balance',
        'colored_status',
        'due_date',
        'priority',
    )
    list_filter = ('status', 'due_date', 'priority', 'is_auto_generated')
    search_fields = (
        'invoice_reference',
        'student__first_name',
        'student__last_name',
        'student__username',
    )
    readonly_fields = AUDIT_READONLY_FIELDS + ('invoice_reference', 'total_amount', 'paid_amount', 'balance')
    inlines = (InvoiceItemInline, PaymentAllocationInline)

    fieldsets = (
        (_('Invoice Header'), {
            'fields': ('invoice_reference', 'student', 'due_date', 'priority', 'is_auto_generated')
        }),
        (_('Financial Summary'), {
            'fields': ('total_amount', 'paid_amount', 'balance'),
            'description': _('Automatically calculated')
        }),
        (_('Admin Control'), {
            'fields': ('status', 'created_by', 'updated_by', 'notes'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )

    def colored_status(self, obj):
        colors = {
            InvoiceStatus.DRAFT: '#666666',
            InvoiceStatus.PENDING: '#FF9800',
            InvoiceStatus.PARTIALLY_PAID: '#2196F3',
            InvoiceStatus.PAID: '#4CAF50',
            InvoiceStatus.OVERDUE: '#F44336',
            InvoiceStatus.CANCELLED: '#9C27B0',
        }
        color = colors.get(obj.computed_status, '#000000')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.computed_status)
    colored_status.short_description = _('Status')


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'fee_item', 'description', 'quantity', 'unit_price', 'amount', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('invoice__invoice_reference', 'fee_item__name')
    readonly_fields = AUDIT_READONLY_FIELDS + ('amount',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_reference',
        'student',
        'amount',
        'allocated_amount',
        'completed_refunded_amount',
        'effective_utilized_amount',
        'unassigned_amount',
        'payment_method',
        'colored_status',
        'created_at',
    )
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('payment_reference', 'mpesa_receipt_number', 'transaction_id', 'student__username')
    readonly_fields = AUDIT_READONLY_FIELDS + (
        'payment_reference',
        'allocated_amount',
        'effective_utilized_amount',
        'completed_refunded_amount',
        'pending_refunded_amount',
        'unassigned_amount',
        'get_available_refund_amount',
    )
    inlines = (PaymentAllocationInline, RefundInline)

    fieldsets = (
        (_('Payment Overview'), {
            'fields': ('payment_reference', 'student', 'amount', 'payment_method', 'status')
        }),
        (_('M-Pesa Details'), {
            'fields': ('mpesa_receipt_number', 'mpesa_phone_number', 'mpesa_transaction_date'),
            'classes': ('collapse',)
        }),
        (_('Bank / Other Details'), {
            'fields': ('bank_reference', 'bank_name', 'transaction_id'),
            'classes': ('collapse',)
        }),
        (_('Allocation & Refund Summary'), {
            'fields': (
                'priority_invoice',
                'allocated_amount',
                'effective_utilized_amount',
                'completed_refunded_amount',
                'pending_refunded_amount',
                'unassigned_amount',
                'get_available_refund_amount',
            ),
            'description': _('All amounts auto-calculated based on allocations and completed refunds'),
        }),
        (_('Reversal Info'), {
            'fields': ('reversal_reason', 'reversed_by', 'reversed_at'),
            'classes': ('collapse',)
        }),
        (_('Verification & Notes'), {
            'fields': ('verified_at', 'verified_by', 'notes', 'metadata'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )

    def colored_status(self, obj):
        colors = {
            PaymentStatus.PENDING: '#FF9800',
            PaymentStatus.COMPLETED: '#4CAF50',
            PaymentStatus.FAILED: '#F44336',
            PaymentStatus.REVERSED: '#9C27B0',
            PaymentStatus.REFUNDED: '#673AB7',
            PaymentStatus.PARTIALLY_REFUNDED: '#2196F3',
        }
        color = colors.get(obj.status, '#000000')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    colored_status.short_description = _('Status')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = (
        'original_payment',
        'student',
        'amount',
        'refund_method',
        'colored_status',
        'processed_by',
        'processed_at',
    )
    list_filter = ('refund_method', 'status', 'processed_at')
    search_fields = ('original_payment__payment_reference', 'mpesa_receipt_number', 'bank_reference')
    readonly_fields = AUDIT_READONLY_FIELDS + ('processed_at', 'student')
    date_hierarchy = 'processed_at'

    fieldsets = (
        (_('Refund Details'), {
            'fields': ('original_payment', 'student', 'amount', 'refund_method', 'status')
        }),
        (_('M-Pesa Refund'), {
            'fields': ('mpesa_receipt_number', 'mpesa_phone_number', 'mpesa_transaction_date'),
            'classes': ('collapse',)
        }),
        (_('Bank Refund'), {
            'fields': ('bank_reference', 'bank_name'),
            'classes': ('collapse',)
        }),
        (_('General'), {
            'fields': ('transaction_id', 'reference', 'notes')
        }),
        (_('Processed'), {
            'fields': ('processed_by', 'processed_at'),
        }),
        (_('Cancellation'), {
            'fields': ('cancelled_by', 'cancelled_at', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )

    def colored_status(self, obj):
        colors = {
            'PENDING': '#FF9800',
            'COMPLETED': '#4CAF50',
            'FAILED': '#F44336',
            'CANCELLED': '#9C27B0',
        }
        color = colors.get(obj.status, '#000000')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    colored_status.short_description = _('Status')

    def student(self, obj):
        return obj.student
    student.short_description = _('Student')
    student.admin_order_field = 'original_payment__student'


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ('payment', 'invoice', 'allocated_amount', 'allocation_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('payment__payment_reference', 'invoice__invoice_reference')
    readonly_fields = AUDIT_READONLY_FIELDS


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ('trans_id', 'bill_ref_number', 'trans_amount', 'msisdn', 'first_name', 'status', 'is_reconciled')
    list_filter = ('status', 'is_reconciled')
    search_fields = ('trans_id', 'bill_ref_number', 'msisdn')
    readonly_fields = AUDIT_READONLY_FIELDS + ('raw_data',)


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'has_budget', 'monthly_budget', 'annual_budget', 'requires_approval', 'is_active')
    list_filter = ('has_budget', 'requires_approval', 'is_active')
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'contact_person', 'phone', 'email', 'payment_terms', 'is_active')
    list_filter = ('school', 'payment_terms', 'is_active')
    search_fields = ('name', 'phone', 'email', 'kra_pin')
    readonly_fields = AUDIT_READONLY_FIELDS


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'head', 'budget_allocated', 'get_budget_utilization', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    def get_budget_utilization(self, obj):
        util = obj.get_budget_utilization()
        color = '#4CAF50' if util < 80 else '#FF9800' if util < 100 else '#F44336'
        return format_html('<span style="color: {}; font-weight: bold;">{}%</span>', color, util)
    get_budget_utilization.short_description = _('Budget Utilized')


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'expense_reference',
        'name',
        'category',
        'department',
        'amount',
        'total_amount',
        'colored_status',
        'expense_date',
    )
    list_filter = ('status', 'category', 'department', 'payment_method', 'expense_date')
    search_fields = ('expense_reference', 'name', 'invoice_number')
    readonly_fields = AUDIT_READONLY_FIELDS + ('expense_reference', 'total_amount')
    inlines = (ExpenseAttachmentInline,)
    date_hierarchy = 'expense_date'

    def colored_status(self, obj):
        colors = {
            ExpenseStatus.DRAFT: '#666666',
            ExpenseStatus.PENDING_APPROVAL: '#FF9800',
            ExpenseStatus.APPROVED: '#2196F3',
            ExpenseStatus.REJECTED: '#F44336',
            ExpenseStatus.PAID: '#4CAF50',
            ExpenseStatus.CANCELLED: '#9C27B0',
        }
        color = colors.get(obj.status, '#000000')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, obj.get_status_display())
    colored_status.short_description = _('Status')


@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    list_display = ('expense', 'file_name', 'file_type', 'file_size', 'uploaded_by')
    list_filter = ('file_type', 'created_at')
    search_fields = ('file_name', 'expense__expense_reference')
    readonly_fields = AUDIT_READONLY_FIELDS


@admin.register(PettyCash)
class PettyCashAdmin(admin.ModelAdmin):
    list_display = ('fund_name', 'custodian', 'current_balance', 'status')
    list_filter = ('status',)
    inlines = (PettyCashTransactionInline,)
    readonly_fields = AUDIT_READONLY_FIELDS


@admin.register(PettyCashTransaction)
class PettyCashTransactionAdmin(admin.ModelAdmin):
    list_display = ('petty_cash_fund', 'transaction_type', 'amount', 'balance_after', 'processed_by')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('description',)
    readonly_fields = AUDIT_READONLY_FIELDS


@admin.register(ExpenseBudget)
class ExpenseBudgetAdmin(admin.ModelAdmin):
    list_display = (
        'fiscal_year',
        'category',
        'department',
        'budget_amount',
        'get_spent_amount',
        'get_utilization_percentage',
        'get_remaining_budget',
    )
    list_filter = ('fiscal_year', 'period', 'category')
    readonly_fields = AUDIT_READONLY_FIELDS + ('get_spent_amount', 'get_utilization_percentage', 'get_remaining_budget')

    def get_spent_amount(self, obj):
        return f"KES {obj.get_spent_amount():,.2f}"
    get_spent_amount.short_description = _('Spent')

    def get_utilization_percentage(self, obj):
        p = obj.get_utilization_percentage()
        color = '#4CAF50' if p < 80 else '#FF9800' if p < 100 else '#F44336'
        return format_html('<span style="color: {}; font-weight: bold;">{:.2f}%</span>', color, p)
    get_utilization_percentage.short_description = _('Utilization %')

    def get_remaining_budget(self, obj):
        return f"KES {obj.get_remaining_budget():,.2f}"
    get_remaining_budget.short_description = _('Remaining')


@admin.register(BalanceSheet)
class BalanceSheetAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_invoiced', 'total_collected', 'total_outstanding', 'total_overdue')
    list_filter = ('date',)
    date_hierarchy = 'date'
    readonly_fields = tuple(f.name for f in BalanceSheet._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
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
    MpesaTransaction,
    ExpenseCategory,
    Vendor,
    Department,
    Expense,
    ExpenseAttachment,
    PettyCash,
    PettyCashTransaction,
    ExpenseBudget,
    BalanceSheet
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
    list_display = ('name', 'category', 'default_amount', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Fee Item Details'), {
            'fields': ('name', 'category', 'default_amount', 'is_active')
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
            'DRAFT': 'gray',
            'PENDING': 'orange',
            'PARTIALLY_PAID': 'blue',
            'PAID': 'green',
            'OVERDUE': 'red',
            'CANCELLED': 'darkred',
        }
        return format_html('<b style="color:{};">{}</b>', colors.get(obj.computed_status, 'black'), obj.computed_status)
    colored_status.short_description = _('Status')


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'fee_item', 'description', 'quantity', 'unit_price', 'amount', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('invoice__invoice_reference', 'fee_item__name')
    readonly_fields = AUDIT_READONLY_FIELDS + ('amount',)

    fieldsets = (
        (_('Item Details'), {
            'fields': ('invoice', 'fee_item', 'description')
        }),
        (_('Pricing'), {
            'fields': ('quantity', 'unit_price', 'amount')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        AUDIT_FIELDSET,
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_reference',
        'student',
        'amount',
        'utilized_amount',
        'unassigned_amount',
        'payment_method',
        'colored_status',
    )
    list_filter = ('payment_method', 'status', 'created_at')
    search_fields = ('payment_reference', 'mpesa_receipt_number', 'transaction_id')
    readonly_fields = AUDIT_READONLY_FIELDS + ('payment_reference', 'utilized_amount', 'unassigned_amount')
    inlines = (PaymentAllocationInline,)

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
        (_('Allocation Summary'), {
            'fields': ('utilized_amount', 'unassigned_amount')
        }),
        (_('Verification & Notes'), {
            'fields': ('verified_at', 'verified_by', 'notes', 'metadata'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )

    def colored_status(self, obj):
        colors = {'PENDING': 'orange', 'COMPLETED': 'green', 'FAILED': 'red', 'REVERSED': 'darkred'}
        return format_html('<b style="color:{};">{}</b>', colors.get(obj.status, 'black'), obj.status)
    colored_status.short_description = _('Status')


@admin.register(PaymentAllocation)
class PaymentAllocationAdmin(admin.ModelAdmin):
    list_display = ('payment', 'invoice', 'allocated_amount', 'allocation_order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('payment__payment_reference', 'invoice__invoice_reference')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Allocation'), {
            'fields': ('payment', 'invoice', 'allocated_amount', 'allocation_order')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        AUDIT_FIELDSET,
    )


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = ('trans_id', 'bill_ref_number', 'trans_amount', 'msisdn', 'first_name', 'status', 'is_reconciled')
    list_filter = ('status', 'is_reconciled')
    search_fields = ('trans_id', 'bill_ref_number', 'msisdn')
    readonly_fields = AUDIT_READONLY_FIELDS + ('raw_data',)

    fieldsets = (
        (_('Transaction Core'), {
            'fields': ('trans_id', 'trans_time', 'trans_amount', 'business_short_code', 'bill_ref_number')
        }),
        (_('Customer Info'), {
            'fields': ('msisdn', 'first_name', 'middle_name', 'last_name')
        }),
        (_('Reconciliation'), {
            'fields': ('payment', 'status', 'is_reconciled', 'reconciliation_notes')
        }),
        (_('Raw Payload'), {
            'fields': ('raw_data',),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ('get_full_path', 'has_budget', 'monthly_budget', 'annual_budget', 'requires_approval', 'is_active')
    list_filter = ('has_budget', 'requires_approval', 'is_active')
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Category'), {
            'fields': ('name', 'parent')
        }),
        (_('Budget Settings'), {
            'fields': ('has_budget', 'monthly_budget', 'annual_budget')
        }),
        (_('Workflow'), {
            'fields': ('requires_approval', 'is_active')
        }),
        AUDIT_FIELDSET,
    )


@admin.register(Vendor)
class VendorAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'email', 'payment_terms', 'is_active')
    list_filter = ('payment_terms', 'is_active')
    search_fields = ('name', 'phone', 'email', 'kra_pin')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Vendor Identity'), {
            'fields': ('name', 'contact_person', 'email', 'phone', 'address', 'kra_pin')
        }),
        (_('Payment Preferences'), {
            'fields': (
                'payment_terms',
                ('mpesa_pochi_number', 'mpesa_paybill_number', 'mpesa_paybill_account', 'mpesa_till_number'),
                ('bank_name', 'bank_account', 'bank_branch'),
            )
        }),
        (_('Status & Notes'), {
            'fields': ('is_active', 'notes'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'head', 'budget_allocated', 'get_budget_utilization', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Department Info'), {
            'fields': ('name', 'head', 'budget_allocated')
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
        AUDIT_FIELDSET,
    )

    def get_budget_utilization(self, obj):
        util = obj.get_budget_utilization()
        color = 'green' if util < 80 else 'orange' if util < 100 else 'red'
        return format_html('<b style="color:{};">{}%</b>', color, util)
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

    fieldsets = (
        (_('Expense Core'), {
            'fields': ('expense_reference', 'name', 'category', 'department', 'vendor', 'amount', 'expense_date')
        }),
        (_('Payment & Status'), {
            'fields': ('payment_method', 'status')
        }),
        (_('Reference Numbers'), {
            'fields': ('invoice_number', 'receipt_number', 'cheque_number', 'transaction_reference'),
            'classes': ('collapse',)
        }),
        (_('Tax'), {
            'fields': ('is_taxable', 'tax_rate', 'tax_amount')
        }),
        (_('Total'), {
            'fields': ('total_amount',),
            'description': _('Amount + Tax (auto-calculated)')
        }),
        (_('Approval Workflow'), {
            'fields': (
                ('requested_by', 'approved_by', 'rejected_by', 'paid_by'),
                ('approved_at', 'rejected_at', 'paid_at'),
                'rejection_reason',
            ),
            'classes': ('collapse',)
        }),
        (_('Recurring'), {
            'fields': ('is_recurring', 'recurrence_frequency'),
            'classes': ('collapse',)
        }),
        (_('Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )

    def colored_status(self, obj):
        colors = {
            'DRAFT': 'gray',
            'PENDING_APPROVAL': 'orange',
            'APPROVED': 'blue',
            'REJECTED': 'red',
            'PAID': 'green',
            'CANCELLED': 'darkred',
        }
        return format_html('<b style="color:{};">{}</b>', colors.get(obj.status, 'black'), obj.status)
    colored_status.short_description = _('Status')


@admin.register(ExpenseAttachment)
class ExpenseAttachmentAdmin(admin.ModelAdmin):
    list_display = ('expense', 'file_name', 'file_type', 'file_size', 'uploaded_by')
    list_filter = ('file_type', 'created_at')
    search_fields = ('file_name', 'expense__expense_reference')
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('File'), {
            'fields': ('expense', 'file')
        }),
        (_('Metadata'), {
            'fields': ('file_name', 'file_type', 'file_size', 'uploaded_by'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )


@admin.register(PettyCash)
class PettyCashAdmin(admin.ModelAdmin):
    list_display = ('fund_name', 'custodian', 'current_balance', 'status')
    list_filter = ('status',)
    inlines = (PettyCashTransactionInline,)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Fund Details'), {
            'fields': ('fund_name', 'custodian', 'initial_amount', 'current_balance', 'status')
        }),
        AUDIT_FIELDSET,
    )


@admin.register(PettyCashTransaction)
class PettyCashTransactionAdmin(admin.ModelAdmin):
    list_display = ('petty_cash_fund', 'transaction_type', 'amount', 'balance_after', 'processed_by')
    list_filter = ('transaction_type', 'created_at')
    search_fields = ('description',)
    readonly_fields = AUDIT_READONLY_FIELDS

    fieldsets = (
        (_('Transaction'), {
            'fields': ('petty_cash_fund', 'transaction_type', 'amount', 'description')
        }),
        (_('Balances'), {
            'fields': ('balance_before', 'balance_after')
        }),
        (_('Processed By'), {
            'fields': ('processed_by', 'expense', 'notes'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )


@admin.register(ExpenseBudget)
class ExpenseBudgetAdmin(admin.ModelAdmin):
    list_display = (
        'fiscal_year',
        'category',
        'department',
        'budget_amount',
        'get_spent_amount',
        'get_utilization_percentage',
    )
    list_filter = ('fiscal_year', 'period', 'category')
    readonly_fields = AUDIT_READONLY_FIELDS + ('get_spent_amount', 'get_utilization_percentage', 'get_remaining_budget')

    fieldsets = (
        (_('Budget Definition'), {
            'fields': ('fiscal_year', 'category', 'department', 'budget_amount', 'period')
        }),
        (_('Date Range'), {
            'fields': ('start_date', 'end_date')
        }),
        (_('Utilization Summary'), {
            'fields': ('get_spent_amount', 'get_utilization_percentage', 'get_remaining_budget')
        }),
        (_('Notes'), {
            'fields': ('notes', 'created_by'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )

    def get_spent_amount(self, obj):
        return f"KES {obj.get_spent_amount():,.2f}"
    get_spent_amount.short_description = _('Spent')

    def get_utilization_percentage(self, obj):
        p = obj.get_utilization_percentage()
        color = 'green' if p < 80 else 'orange' if p < 100 else 'red'
        return format_html('<b style="color:{};">{:.2f}%</b>', color, p)
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

    fieldsets = (
        (_('Financial Summary'), {
            'fields': (
                'total_invoiced',
                'total_collected',
                'total_outstanding',
                'total_overdue',
                'mpesa_collections',
                'bank_collections',
                'cash_collections',
            )
        }),
        (_('Counts'), {
            'fields': (
                'number_of_invoices',
                'number_of_payments',
                'number_of_paid_invoices',
                'number_of_pending_invoices',
            )
        }),
        (_('Generated'), {
            'fields': ('date', 'generated_by', 'metadata'),
            'classes': ('collapse',)
        }),
        AUDIT_FIELDSET,
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
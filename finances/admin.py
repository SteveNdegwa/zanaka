from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from .models import (
    Invoice, InvoiceItem, Payment, PaymentAllocation,
    MpesaTransaction, FeeItem, GradeLevelFee, BalanceSheet
)


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = (
        'fee_item', 'description', 'quantity', 'unit_price',
        'amount', 'is_active', 'created_at', 'updated_at'
    )


class PaymentAllocationInline(admin.TabularInline):
    model = PaymentAllocation
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = (
        'payment', 'invoice', 'allocated_amount', 'allocation_order',
        'is_active', 'created_at', 'updated_at'
    )


@admin.register(FeeItem)
class FeeItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'default_amount', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Item Info', {
            'fields': ('name', 'category', 'default_amount')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(GradeLevelFee)
class GradeLevelFeeAdmin(admin.ModelAdmin):
    list_display = ('fee_item', 'grade_level', 'term', 'academic_year', 'amount', 'is_mandatory')
    list_filter = ('grade_level', 'term', 'academic_year', 'is_mandatory')
    search_fields = ('fee_item__name',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Fee Mapping', {
            'fields': ('fee_item', 'grade_level', 'term', 'academic_year')
        }),
        ('Amounts', {
            'fields': ('amount', 'is_mandatory')
        }),
        ('Audit', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_reference', 'student', 'status', 'priority', 'total_amount',
        'paid_amount', 'balance', 'due_date', 'created_at'
    )

    list_filter = (
        'status', 'priority',
        ('due_date', DateFieldListFilter),
        ('created_at', DateFieldListFilter),
        ('updated_at', DateFieldListFilter),
    )

    search_fields = (
        'invoice_reference', 'student__id',
        'student__first_name', 'student__last_name'
    )

    inlines = [InvoiceItemInline, PaymentAllocationInline]

    readonly_fields = ('invoice_reference', 'created_at', 'updated_at')

    fieldsets = (
        ('Invoice Identification', {
            'fields': (
                'invoice_reference', 'student',
                'status', 'priority', 'is_auto_generated'
            )
        }),
        ('Financial Summary', {
            'fields': ('total_amount', 'paid_amount', 'balance')
        }),
        ('Dates', {
            'fields': ('due_date', 'created_at', 'updated_at')
        }),
        ('Notes & Audit', {
            'fields': ('notes', 'created_by', 'updated_by')
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'payment_reference', 'student', 'payment_method', 'amount',
        'utilized_amount', 'status', 'created_at'
    )

    list_filter = (
        'payment_method', 'status',
        ('created_at', DateFieldListFilter),
        ('updated_at', DateFieldListFilter),
    )

    search_fields = (
        'student__id', 'student__reg_number', 'student__first_name', 'student__last_name',
        'payment_reference', 'mpesa_receipt_number', 'bank_reference', 'transaction_id'
    )

    inlines = [PaymentAllocationInline]

    readonly_fields = ('payment_reference', 'unassigned_amount', 'created_at', 'updated_at')

    fieldsets = (
        ('Payment Identification', {
            'fields': ('payment_reference', 'payment_method', 'status')
        }),
        ('Amounts', {
            'fields': ('amount', 'utilized_amount', 'unassigned_amount')
        }),
        ('M-Pesa Details', {
            'fields': (
                'mpesa_receipt_number', 'mpesa_phone_number',
                'mpesa_transaction_date'
            )
        }),
        ('Bank Details', {
            'fields': ('bank_reference', 'bank_name', 'transaction_id')
        }),
        ('Verification', {
            'fields': ('verified_by', 'verified_at')
        }),
        ('Notes & Audit', {
            'fields': ('notes', 'metadata', 'created_at', 'updated_at')
        }),
    )


@admin.register(MpesaTransaction)
class MpesaTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'trans_id', 'trans_amount', 'msisdn',
        'bill_ref_number', 'status',
        'is_reconciled', 'created_at'
    )

    list_filter = (
        'status', 'is_reconciled',
        ('created_at', DateFieldListFilter),
        ('updated_at', DateFieldListFilter),
    )

    search_fields = ('trans_id', 'bill_ref_number', 'msisdn')

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Transaction Info', {
            'fields': (
                'transaction_type', 'trans_id', 'trans_amount',
                'trans_time', 'business_short_code', 'bill_ref_number'
            )
        }),
        ('Customer Info', {
            'fields': ('msisdn', 'first_name', 'middle_name', 'last_name')
        }),
        ('Reconciliation', {
            'fields': ('payment', 'is_reconciled', 'reconciliation_notes')
        }),
        ('Raw Data & Audit', {
            'fields': ('raw_data', 'created_at', 'updated_at')
        }),
    )


@admin.register(BalanceSheet)
class BalanceSheetAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'total_invoiced', 'total_collected',
        'total_outstanding', 'total_overdue',
        'mpesa_collections', 'bank_collections', 'cash_collections'
    )

    list_filter = (('date', DateFieldListFilter),)

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Period', {
            'fields': ('date',)
        }),
        ('Financial Summary', {
            'fields': (
                'total_invoiced', 'total_collected',
                'total_outstanding', 'total_overdue'
            )
        }),
        ('Collections Breakdown', {
            'fields': (
                'mpesa_collections', 'bank_collections', 'cash_collections'
            )
        }),
        ('Counts', {
            'fields': (
                'number_of_invoices', 'number_of_payments',
                'number_of_paid_invoices', 'number_of_pending_invoices'
            )
        }),
        ('Audit', {
            'fields': ('generated_by', 'metadata', 'created_at', 'updated_at')
        }),
    )

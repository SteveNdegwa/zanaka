from django.urls import path

from . import views

urlpatterns = [
    # Invoice management
    path('students/<str:student_id>/invoices/create/', views.create_invoice, name='create-invoice'),
    path('invoices/<str:invoice_id>/update/', views.update_invoice, name='update-invoice'),
    path('invoices/<str:invoice_id>/cancel/', views.cancel_invoice, name='cancel-invoice'),
    path('invoices/<str:invoice_id>/activate/', views.activate_invoice, name='activate-invoice'),
    path('invoices/<str:invoice_id>/', views.view_invoice, name='view-invoice'),
    path('invoices/', views.list_invoices, name='list-invoices'),

    # Bulk invoice management
    path('bulk-invoices/create/', views.bulk_create_invoices, name='bulk-create-invoices'),
    path('bulk-invoices/<str:bulk_invoice_id>/', views.view_bulk_invoice, name='view-bulk-invoice'),
    path('bulk-invoices/<str:bulk_invoice_id>/cancel/', views.bulk_cancel_invoices, name='bulk-cancel-invoices'),
    path('bulk-invoices/', views.list_bulk_invoices, name='list-bulk-invoices'),

    #v  Payment management
    path('students/<str:student_id>/payments/create/', views.create_payment, name='create-payment'),
    path('payments/<str:payment_id>/approve/', views.approve_payment, name='approve-payment'),
    path('payments/<str:payment_id>/reverse/', views.reverse_payment, name='reverse-payment'),
    path('payments/<str:payment_id>/refunds/create/', views.create_refund, name='create-refund'),
    path('refunds/<str:refund_id>/cancel/', views.cancel_refund, name='create-refund'),
    path('payments/<str:payment_id>/', views.view_payment, name='view-payment'),
    path('payments/', views.list_payments, name='list-payments'),

    # Expense management
    path('expenses/create/', views.create_expense, name='create-expense'),
    path('expenses/<str:expense_id>/update/', views.update_expense, name='update-expense'),
    path('expenses/<str:expense_id>/submit/', views.submit_expense_for_approval, name='submit-expense'),
    path('expenses/<str:expense_id>/approve/', views.approve_expense, name='approve-expense'),
    path('expenses/<str:expense_id>/reject/', views.reject_expense, name='reject-expense'),
    path('expenses/<str:expense_id>/pay/', views.mark_expense_as_paid, name='pay-expense'),
    path('expenses/<str:expense_id>/cancel/', views.cancel_expense, name='cancel-expense'),
    path('expenses/<str:expense_id>/', views.view_expense, name='view-expense'),
    path('expenses/', views.list_expenses, name='list-expenses'),
    path('expenses/summary/', views.get_expense_summary, name='expense-summary'),

    # Expense attachments
    path(
        'expenses/<str:expense_id>/attachments/add/',
        views.add_expense_attachment,
        name='add-expense-attachment'
    ),
    path(
        'expenses/attachments/<str:attachment_id>/remove/',
        views.remove_expense_attachment,
        name='remove-expense-attachment'
    ),

    # Vendor management
    path('vendors/create/', views.create_vendor, name='create-vendor'),
    path('vendors/<str:vendor_id>/update/', views.update_vendor, name='update-vendor'),
    path('vendors/<str:vendor_id>/deactivate/', views.deactivate_vendor, name='deactivate-vendor'),
    path('vendors/<str:vendor_id>/activate/', views.activate_vendor, name='activate-vendor'),
    path('vendors/<str:vendor_id>/', views.view_vendor, name='view-vendor'),
    path('vendors/', views.list_vendors, name='list-vendors'),

    # Petty cash management
    path('petty-cash/create/', views.create_petty_cash_fund, name='create-petty-cash-fund'),
    path('petty-cash/<str:fund_id>/replenish/', views.replenish_petty_cash, name='replenish-petty-cash'),
    path('petty-cash/<str:fund_id>/close/', views.close_petty_cash_fund, name='close-petty-cash-fund'),
    path('petty-cash/<str:fund_id>/reopen/', views.reopen_petty_cash_fund, name='reopen-petty-cash-fund'),
    path('petty-cash/<str:fund_id>/', views.view_petty_cash_fund, name='view-petty-cash-fund'),
    path('petty-cash/', views.list_petty_cash_funds, name='list-petty-cash-funds'),
    path(
        'petty-cash/<str:fund_id>/transactions/',
        views.view_petty_cash_transactions,
        name='view-petty-cash-transactions'
    ),

    # Department management
    path('departments/create/', views.create_department, name='create-department'),
    path('departments/<str:department_id>/update/', views.update_department, name='update-department'),
    path('departments/<str:department_id>/deactivate/', views.deactivate_department, name='deactivate-department'),
    path('departments/<str:department_id>/activate/', views.activate_department, name='activate-department'),
    path('departments/<str:department_id>/', views.view_department, name='view-department'),
    path('departments/', views.list_departments, name='list-departments'),
    path(
        'departments/<str:department_id>/expense-breakdown/',
        views.get_department_expense_breakdown,
        name='department-expense-breakdown'
    ),

    # Expense budget management
    path('expense-budgets/create/', views.create_expense_budget, name='create-expense-budget'),
    path('expense-budgets/<str:budget_id>/update/', views.update_expense_budget, name='update-expense-budget'),
    path('expense-budgets/<str:budget_id>/delete/', views.delete_expense_budget, name='delete-expense-budget'),
    path('expense-budgets/<str:budget_id>/', views.view_expense_budget, name='view-expense-budget'),
    path('expense-budgets/', views.list_expense_budgets, name='list-expense-budgets'),
    path(
        'expense-budgets/utilization-report/',
        views.get_budget_utilization_report,
        name='budget-utilization-report'
    ),

    # Fee items management
    path('fee-items/create/', views.create_fee_item, name='create_fee_item'),
    path('fee-items/<str:fee_item_id>/update/', views.update_fee_item, name='update_fee_item'),
    path('fee-items/<str:fee_item_id>/deactivate/', views.deactivate_fee_item, name='deactivate_fee_item'),
    path('fee-items/<str:fee_item_id>/activate/', views.activate_fee_item, name='activate_fee_item'),
    path('fee-items/<str:fee_item_id>/', views.view_fee_item, name='view_fee_item'),
    path('fee-items/', views.list_fee_items, name='list_fee_items'),
    path(
        'fee-items/<str:fee_item_id>/grade-level-fees/create/',
        views.create_grade_level_fee,
        name='create_grade_level_fee'
    ),
    path(
        'grade-level-fees/<str:grade_level_fee_id>/update/',
        views.update_grade_level_fee,
        name='update_grade_level_fee'
    ),
    path(
        'grade-level-fees/<str:grade_level_fee_id>/delete/',
        views.delete_grade_level_fee,
        name='delete_grade_level_fee'
    ),
]
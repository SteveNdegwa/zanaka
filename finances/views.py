from django.http import JsonResponse

from finances.services.department_services import DepartmentServices
from finances.services.expense_budget_services import ExpenseBudgetServices
from finances.services.expense_services import ExpenseServices
from finances.services.invoice_services import InvoiceServices
from finances.services.payment_services import PaymentServices
from finances.services.petty_cash_services import PettyCashServices
from finances.services.vendor_services import VendorServices
from utils.decorators.user_login_required import user_login_required
from utils.extended_request import ExtendedRequest
from utils.response_provider import ResponseProvider


@user_login_required(required_permission='finances.create_invoice')
def create_invoice(request: ExtendedRequest, student_id) -> JsonResponse:
    invoice = InvoiceServices.create_invoice(
        user=request.user,
        student_id=student_id,
        **request.data
    )

    return ResponseProvider.created(
        message='Invoice created successfully',
        data={'id': str(invoice.id)}
    )


@user_login_required(required_permission='finances.update_invoice')
def update_invoice(request: ExtendedRequest, invoice_id) -> JsonResponse:
    InvoiceServices.update_invoice(
        user=request.user,
        invoice_id=invoice_id,
        **request.data
    )

    return ResponseProvider.success(
        message='Invoice updated successfully'
    )


@user_login_required(required_permission='finances.cancel_invoice')
def cancel_invoice(request: ExtendedRequest, invoice_id) -> JsonResponse:
    InvoiceServices.cancel_invoice(
        user=request.user,
        invoice_id=invoice_id
    )

    return ResponseProvider.success(
        message='Invoice cancelled successfully'
    )


@user_login_required(required_permission='finances.activate_invoice')
def activate_invoice(request: ExtendedRequest, invoice_id) -> JsonResponse:
    InvoiceServices.activate_invoice(
        user=request.user,
        invoice_id=invoice_id
    )

    return ResponseProvider.success(
        message='Invoice activated successfully'
    )


@user_login_required(required_permission='finances.view_invoice')
def view_invoice(request: ExtendedRequest, invoice_id) -> JsonResponse:
    invoice = InvoiceServices.fetch_invoice(invoice_id=invoice_id)

    return ResponseProvider.success(
        message='Invoice fetched successfully',
        data=invoice
    )


@user_login_required(required_permission='finances.list_invoices')
def list_invoices(request: ExtendedRequest) -> JsonResponse:
    invoices = InvoiceServices.filter_invoices(**request.data)

    return ResponseProvider.success(
        message='Invoices fetched successfully',
        data=invoices
    )


@user_login_required(required_permission='finances.create_payment')
def create_payment(request: ExtendedRequest, student_id) -> JsonResponse:
    payment = PaymentServices.create_payment(
        user=request.user,
        student_id=student_id,
        **request.data
    )

    return ResponseProvider.created(
        message='Payment created successfully',
        data={'id': str(payment.id)}
    )


@user_login_required(required_permission='finances.reverse_payment')
def reverse_payment(request: ExtendedRequest, payment_id) -> JsonResponse:
    PaymentServices.reverse_payment(payment_id=payment_id)

    return ResponseProvider.success(
        message='Payment reversed successfully'
    )


@user_login_required(required_permission='finances.view_payment')
def view_payment(request: ExtendedRequest, payment_id) -> JsonResponse:
    payment = PaymentServices.fetch_payment(payment_id=payment_id)

    return ResponseProvider.success(
        message='Payment fetched successfully',
        data=payment
    )


@user_login_required(required_permission='finances.list_payments')
def list_payments(request: ExtendedRequest) -> JsonResponse:
    payments = PaymentServices.filter_payments(**request.data)

    return ResponseProvider.success(
        message='Payments fetched successfully',
        data=payments
    )


@user_login_required(required_permission='finances.create_expense')
def create_expense(request: ExtendedRequest) -> JsonResponse:
    expense = ExpenseServices.create_expense(
        user=request.user,
        **request.data
    )

    return ResponseProvider.created(
        message='Expense created successfully',
        data={'id': str(expense.id)}
    )


@user_login_required(required_permission='finances.update_expense')
def update_expense(request: ExtendedRequest, expense_id) -> JsonResponse:
    ExpenseServices.update_expense(
        user=request.user,
        expense_id=expense_id,
        **request.data
    )

    return ResponseProvider.success(
        message='Expense updated successfully'
    )


@user_login_required(required_permission='finances.submit_expense')
def submit_expense_for_approval(request: ExtendedRequest, expense_id) -> JsonResponse:
    ExpenseServices.submit_for_approval(
        user=request.user,
        expense_id=expense_id
    )

    return ResponseProvider.success(
        message='Expense submitted for approval successfully'
    )


@user_login_required(required_permission='finances.approve_expense')
def approve_expense(request: ExtendedRequest, expense_id) -> JsonResponse:
    ExpenseServices.approve_expense(
        user=request.user,
        expense_id=expense_id
    )

    return ResponseProvider.success(
        message='Expense approved successfully'
    )


@user_login_required(required_permission='finances.approve_expense')
def reject_expense(request: ExtendedRequest, expense_id) -> JsonResponse:
    rejection_reason = request.data.get('rejection_reason', '')

    ExpenseServices.reject_expense(
        user=request.user,
        expense_id=expense_id,
        rejection_reason=rejection_reason
    )

    return ResponseProvider.success(
        message='Expense rejected successfully'
    )


@user_login_required(required_permission='finances.pay_expense')
def mark_expense_as_paid(request: ExtendedRequest, expense_id) -> JsonResponse:
    payment_method = request.data.get('payment_method')

    ExpenseServices.mark_as_paid(
        user=request.user,
        expense_id=expense_id,
        payment_method=payment_method,
        **request.data
    )

    return ResponseProvider.success(
        message='Expense marked as paid successfully'
    )


@user_login_required(required_permission='finances.cancel_expense')
def cancel_expense(request: ExtendedRequest, expense_id) -> JsonResponse:
    ExpenseServices.cancel_expense(
        user=request.user,
        expense_id=expense_id
    )

    return ResponseProvider.success(
        message='Expense cancelled successfully'
    )


@user_login_required(required_permission='finances.view_expense')
def view_expense(request: ExtendedRequest, expense_id) -> JsonResponse:
    expense = ExpenseServices.fetch_expense(expense_id=expense_id)

    return ResponseProvider.success(
        message='Expense fetched successfully',
        data=expense
    )


@user_login_required(required_permission='finances.list_expenses')
def list_expenses(request: ExtendedRequest) -> JsonResponse:
    expenses = ExpenseServices.filter_expenses(**request.data)

    return ResponseProvider.success(
        message='Expenses fetched successfully',
        data=expenses
    )


@user_login_required(required_permission='finances.view_expense_summary')
def get_expense_summary(request: ExtendedRequest) -> JsonResponse:
    summary = ExpenseServices.get_expense_summary(**request.data)

    return ResponseProvider.success(
        message='Expense summary fetched successfully',
        data=summary
    )


@user_login_required(required_permission='finances.upload_expense_attachment')
def add_expense_attachment(request: ExtendedRequest, expense_id) -> JsonResponse:
    file = request.FILES.get('file')

    if not file:
        return ResponseProvider.bad_request(
            message='File is required'
        )

    attachment = ExpenseServices.add_attachment(
        user=request.user,
        expense_id=expense_id,
        file=file
    )

    return ResponseProvider.created(
        message='Attachment added successfully',
        data={'id': str(attachment.id)}
    )


@user_login_required(required_permission='finances.delete_expense_attachment')
def remove_expense_attachment(request: ExtendedRequest, attachment_id) -> JsonResponse:
    ExpenseServices.remove_attachment(
        user=request.user,
        attachment_id=attachment_id
    )

    return ResponseProvider.success(
        message='Attachment removed successfully'
    )


@user_login_required(required_permission='finances.create_vendor')
def create_vendor(request: ExtendedRequest) -> JsonResponse:
    vendor = VendorServices.create_vendor(
        user=request.user,
        **request.data
    )

    return ResponseProvider.created(
        message='Vendor created successfully',
        data={'id': str(vendor.id)}
    )


@user_login_required(required_permission='finances.update_vendor')
def update_vendor(request: ExtendedRequest, vendor_id) -> JsonResponse:
    VendorServices.update_vendor(
        user=request.user,
        vendor_id=vendor_id,
        **request.data
    )

    return ResponseProvider.success(
        message='Vendor updated successfully'
    )


@user_login_required(required_permission='finances.deactivate_vendor')
def deactivate_vendor(request: ExtendedRequest, vendor_id) -> JsonResponse:
    VendorServices.deactivate_vendor(
        user=request.user,
        vendor_id=vendor_id
    )

    return ResponseProvider.success(
        message='Vendor deactivated successfully'
    )


@user_login_required(required_permission='finances.activate_vendor')
def activate_vendor(request: ExtendedRequest, vendor_id) -> JsonResponse:
    VendorServices.activate_vendor(
        user=request.user,
        vendor_id=vendor_id
    )

    return ResponseProvider.success(
        message='Vendor activated successfully'
    )


@user_login_required(required_permission='finances.view_vendor')
def view_vendor(request: ExtendedRequest, vendor_id) -> JsonResponse:
    vendor = VendorServices.fetch_vendor(vendor_id=vendor_id)

    return ResponseProvider.success(
        message='Vendor fetched successfully',
        data=vendor
    )


@user_login_required(required_permission='finances.list_vendors')
def list_vendors(request: ExtendedRequest) -> JsonResponse:
    vendors = VendorServices.filter_vendors(**request.data)

    return ResponseProvider.success(
        message='Vendors fetched successfully',
        data=vendors
    )


@user_login_required(required_permission='finances.create_petty_cash_fund')
def create_petty_cash_fund(request: ExtendedRequest) -> JsonResponse:
    fund = PettyCashServices.create_petty_cash_fund(
        user=request.user,
        **request.data
    )

    return ResponseProvider.created(
        message='Petty cash fund created successfully',
        data={'id': str(fund.id)}
    )


@user_login_required(required_permission='finances.replenish_petty_cash')
def replenish_petty_cash(request: ExtendedRequest, fund_id) -> JsonResponse:
    amount = request.data.get('amount')
    notes = request.data.get('notes', '')

    PettyCashServices.replenish_petty_cash(
        user=request.user,
        fund_id=fund_id,
        amount=amount,
        notes=notes
    )

    return ResponseProvider.success(
        message='Petty cash fund replenished successfully'
    )


@user_login_required(required_permission='finances.close_petty_cash_fund')
def close_petty_cash_fund(request: ExtendedRequest, fund_id) -> JsonResponse:
    PettyCashServices.close_petty_cash_fund(
        user=request.user,
        fund_id=fund_id
    )

    return ResponseProvider.success(
        message='Petty cash fund closed successfully'
    )


@user_login_required(required_permission='finances.reopen_petty_cash_fund')
def reopen_petty_cash_fund(request: ExtendedRequest, fund_id) -> JsonResponse:
    PettyCashServices.reopen_petty_cash_fund(
        user=request.user,
        fund_id=fund_id
    )

    return ResponseProvider.success(
        message='Petty cash fund reopened successfully'
    )


@user_login_required(required_permission='finances.view_petty_cash_fund')
def view_petty_cash_fund(request: ExtendedRequest, fund_id) -> JsonResponse:
    fund = PettyCashServices.fetch_petty_cash_fund(fund_id=fund_id)

    return ResponseProvider.success(
        message='Petty cash fund fetched successfully',
        data=fund
    )


@user_login_required(required_permission='finances.list_petty_cash_funds')
def list_petty_cash_funds(request: ExtendedRequest) -> JsonResponse:
    funds = PettyCashServices.filter_petty_cash_funds(**request.data)

    return ResponseProvider.success(
        message='Petty cash funds fetched successfully',
        data=funds
    )


@user_login_required(required_permission='finances.view_petty_cash_transactions')
def view_petty_cash_transactions(request: ExtendedRequest, fund_id) -> JsonResponse:
    transactions = PettyCashServices.fetch_petty_cash_transactions(
        fund_id=fund_id,
        **request.data
    )

    return ResponseProvider.success(
        message='Petty cash transactions fetched successfully',
        data=transactions
    )


@user_login_required(required_permission='finances.create_department')
def create_department(request: ExtendedRequest) -> JsonResponse:
    department = DepartmentServices.create_department(
        user=request.user,
        **request.data
    )

    return ResponseProvider.created(
        message='Department created successfully',
        data={'id': str(department.id)}
    )


@user_login_required(required_permission='finances.update_department')
def update_department(request: ExtendedRequest, department_id) -> JsonResponse:
    DepartmentServices.update_department(
        user=request.user,
        department_id=department_id,
        **request.data
    )

    return ResponseProvider.success(
        message='Department updated successfully'
    )


@user_login_required(required_permission='finances.deactivate_department')
def deactivate_department(request: ExtendedRequest, department_id) -> JsonResponse:
    DepartmentServices.deactivate_department(
        user=request.user,
        department_id=department_id
    )

    return ResponseProvider.success(
        message='Department deactivated successfully'
    )


@user_login_required(required_permission='finances.activate_department')
def activate_department(request: ExtendedRequest, department_id) -> JsonResponse:
    DepartmentServices.activate_department(
        user=request.user,
        department_id=department_id
    )

    return ResponseProvider.success(
        message='Department activated successfully'
    )


@user_login_required(required_permission='finances.view_department')
def view_department(request: ExtendedRequest, department_id) -> JsonResponse:
    department = DepartmentServices.fetch_department(department_id=department_id)

    return ResponseProvider.success(
        message='Department fetched successfully',
        data=department
    )


@user_login_required(required_permission='finances.list_departments')
def list_departments(request: ExtendedRequest) -> JsonResponse:
    departments = DepartmentServices.filter_departments(**request.data)

    return ResponseProvider.success(
        message='Departments fetched successfully',
        data=departments
    )


@user_login_required(required_permission='finances.view_department_expense_breakdown')
def get_department_expense_breakdown(request: ExtendedRequest, department_id) -> JsonResponse:
    breakdown = DepartmentServices.get_department_expense_breakdown(
        department_id=department_id,
        **request.data
    )

    return ResponseProvider.success(
        message='Department expense breakdown fetched successfully',
        data=breakdown
    )



@user_login_required(required_permission='finances.create_expense_budget')
def create_expense_budget(request: ExtendedRequest) -> JsonResponse:
    budget = ExpenseBudgetServices.create_expense_budget(
        user=request.user,
        **request.data
    )

    return ResponseProvider.created(
        message='Expense budget created successfully',
        data={'id': str(budget.id)}
    )


@user_login_required(required_permission='finances.update_expense_budget')
def update_expense_budget(request: ExtendedRequest, budget_id) -> JsonResponse:
    ExpenseBudgetServices.update_expense_budget(
        user=request.user,
        budget_id=budget_id,
        **request.data
    )

    return ResponseProvider.success(
        message='Expense budget updated successfully'
    )


@user_login_required(required_permission='finances.delete_expense_budget')
def delete_expense_budget(request: ExtendedRequest, budget_id) -> JsonResponse:
    ExpenseBudgetServices.delete_expense_budget(
        user=request.user,
        budget_id=budget_id
    )

    return ResponseProvider.success(
        message='Expense budget deleted successfully'
    )


@user_login_required(required_permission='finances.view_expense_budget')
def view_expense_budget(request: ExtendedRequest, budget_id) -> JsonResponse:
    budget = ExpenseBudgetServices.fetch_expense_budget(budget_id=budget_id)

    return ResponseProvider.success(
        message='Expense budget fetched successfully',
        data=budget
    )


@user_login_required(required_permission='finances.list_expense_budgets')
def list_expense_budgets(request: ExtendedRequest) -> JsonResponse:
    budgets = ExpenseBudgetServices.filter_expense_budgets(**request.data)

    return ResponseProvider.success(
        message='Expense budgets fetched successfully',
        data=budgets
    )


@user_login_required(required_permission='finances.view_budget_utilization')
def get_budget_utilization_report(request: ExtendedRequest) -> JsonResponse:
    report = ExpenseBudgetServices.get_budget_utilization_report(**request.data)

    return ResponseProvider.success(
        message='Budget utilization report fetched successfully',
        data=report
    )
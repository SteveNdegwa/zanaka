from finances.services.invoice_services import InvoiceServices
from finances.services.payment_services import PaymentServices
from utils.decorators.user_login_required import user_login_required
from utils.response_provider import ResponseProvider


@user_login_required(required_permission="can_create_invoice")
def create_invoice(request, student_id):
    invoice = InvoiceServices.create_invoice(
        user=request.user,
        student_id=student_id,
        **request.data
    )

    return ResponseProvider.created(
        message="Invoice created successfully",
        data={"id": str(invoice.id)}
    )


@user_login_required(required_permission="can_update_invoice")
def update_invoice(request, invoice_id):
    InvoiceServices.update_invoice(
        user=request.user,
        invoice_id=invoice_id,
        **request.data
    )

    return ResponseProvider.success(
        message="Invoice updated successfully"
    )


@user_login_required(required_permission="can_cancel_invoice")
def cancel_invoice(request, invoice_id):
    InvoiceServices.cancel_invoice(
        user=request.user,
        invoice_id=invoice_id
    )

    return ResponseProvider.success(
        message="Invoice cancelled successfully"
    )


@user_login_required(required_permission="can_activate_invoice")
def activate_invoice(request, invoice_id):
    InvoiceServices.activate_invoice(
        user=request.user,
        invoice_id=invoice_id
    )

    return ResponseProvider.success(
        message="Invoice activated successfully"
    )


@user_login_required(required_permission="can_view_invoice")
def view_invoice(request, invoice_id):
    invoice = InvoiceServices.fetch_invoice(invoice_id=invoice_id)

    return ResponseProvider.success(
        message="Invoice fetched successfully",
        data=invoice
    )


@user_login_required(required_permission="can_list_invoices")
def list_invoices(request):
    invoices = InvoiceServices.filter_invoices(**request.data)

    return ResponseProvider.success(
        message="Invoices fetched successfully",
        data=invoices
    )


@user_login_required(required_permission="can_create_payment")
def create_payment(request, student_id):
    payment = PaymentServices.create_payment(
        user=request.user,
        student_id=student_id,
        **request.data
    )

    return ResponseProvider.created(
        message="Payment created successfully",
        data={"id": str(payment.id)}
    )


@user_login_required(required_permission="can_reverse_payment")
def reverse_payment(request, payment_id):
    PaymentServices.reverse_payment(payment_id=payment_id)

    return ResponseProvider.success(
        message="Payment reversed successfully"
    )


@user_login_required(required_permission="can_view_payment")
def view_payment(request, payment_id):
    payment = PaymentServices.fetch_payment(payment_id=payment_id)

    return ResponseProvider.success(
        message="Payment fetched successfully",
        data=payment
    )


@user_login_required(required_permission="can_list_payments")
def list_payments(request):
    payments = PaymentServices.filter_payments(**request.data)

    return ResponseProvider.success(
        message="Payments fetched successfully",
        data=payments
    )
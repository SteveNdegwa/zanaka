from django.urls import path

from . import views

urlpatterns = [
    # Invoice management
    path("students/<str:student_id>/invoices/create/", views.create_invoice, name="create-invoice"),
    path("invoices/<str:invoice_id>/update/", views.update_invoice, name="update-invoice"),
    path("invoices/<str:invoice_id>/cancel/", views.cancel_invoice, name="cancel-invoice"),
    path("invoices/<str:invoice_id>/activate/", views.activate_invoice, name="activate-invoice"),
    path("invoices/<str:invoice_id>/", views.view_invoice, name="view-invoice"),
    path("invoices/", views.list_invoices, name="list-invoice"),

    # Payment management
    path("students/<str:student_id>/payments/create/", views.create_payment, name="create-payment"),
    path("payments/<str:payment_id>/reverse/", views.reverse_payment, name="reverse-payment"),
    path("payments/<str:payment_id>/", views.view_payment, name="view-payment"),
    path("payments/", views.list_payments, name="list-payments"),
]

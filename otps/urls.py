from django.urls import path

from otps.views import OTPView

urlpatterns = [
    path('<str:action>/', OTPView.as_view(), name='otps'),
]

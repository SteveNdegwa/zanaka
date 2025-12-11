from django.urls import path

from notifications.views import belio_sms_provider_callback

urlpatterns = [
    path('belio-sms-callback/', belio_sms_provider_callback, name='belio_sms_provider_callback'),
]
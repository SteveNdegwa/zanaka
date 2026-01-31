from django.urls import path, include

from .views import health_check

urlpatterns = [
    path('health/', health_check, name='health'),
    path('auth/', include('authentication.urls')),
    path('finances/', include('finances.urls')),
    path('otps/', include('otps.urls')),
    path('notifications/', include('notifications.urls')),
    path('schools/', include('schools.urls')),
    path('users/', include('users.urls')),
]

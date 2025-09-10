from django.urls import path, include

urlpatterns = [
    path('audit/', include('audit.urls')),
    path('auth/', include('authentication.urls')),
    path('notifications/', include('notifications.urls')),
    path('otps/', include('otps.urls')),
    path('school/', include('school.urls')),
    path('users/', include('users.urls')),
]
from django.urls import path, include

urlpatterns = [
    path('auth/', include('authentication.urls')),
    path('finances/', include('finances.urls')),
    path('otps/', include('otps.urls')),
    path('notifications/', include('notifications.urls')),
    path('schools/', include('schools.urls')),
    path('users/', include('users.urls')),
]

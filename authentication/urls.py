from django.urls import path

from authentication.views import AuthView

urlpatterns = [
    path('<str:action>/', AuthView.as_view(), name='auth'),
]
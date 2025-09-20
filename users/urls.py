from django.urls import path

from users.views.student_guardian_views import StudentGuardianView
from users.views.user_views import UserView

urlpatterns = [
    path('', UserView.as_view(), name='users'),
    path('<str:user_id>/', UserView.as_view(), name='user'),
    path(
        'students/<str:student_id>/guardians/<str:guardian_id>/',
        StudentGuardianView.as_view(),
        name='student-guardian-link',
    )
]
from django.urls import path
from users import views

urlpatterns = [
    # User management
    path('users/create/<str:role_name>/', views.create_user, name='create_user'),
    path('users/update/<str:user_id>/', views.update_user, name='update_user'),
    path('users/delete/<str:user_id>/', views.delete_user, name='delete_user'),
    path('users/<str:user_id>/', views.view_user, name='view_user'),
    path('users/filter/', views.list_users, name='list_users'),

    # Password management
    path('users/forgot-password/', views.forgot_password, name='forgot_password'),
    path('users/reset-password/<str:user_id>/', views.reset_password, name='reset_password'),
    path('users/change-password/', views.change_password, name='change_password'),

    # Guardian management
    path('students/<str:student_id>/guardians/add/', views.add_guardian, name='add_guardian'),
    path('students/<str:student_id>/guardians/<str:guardian_id>/remove/', views.remove_guardian, name='remove_guardian'),
    path('students/<str:student_id>/guardians/', views.list_guardians, name='list_guardians'),
]

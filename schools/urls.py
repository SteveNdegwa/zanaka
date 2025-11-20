from django.urls import path
from schools import views

urlpatterns = [
    # Schools
    path('', views.list_schools, name='list_schools'),
    path('create/', views.create_school, name='create_school'),
    path('<str:school_id>/', views.view_school, name='view_school'),
    path('<str:school_id>/update/', views.update_school, name='update_school'),
    path('<str:school_id>/delete/', views.delete_school, name='delete_school'),

    # Branches
    path('<str:school_id>/branches/', views.list_branches, name='list_branches'),
    path('<str:school_id>/branches/create/', views.create_branch, name='create_branch'),
    path('branches/<str:branch_id>/', views.view_branch, name='view_branch'),
    path('branches/<str:branch_id>/update/', views.update_branch, name='update_branch'),
    path('branches/<str:branch_id>/delete/', views.delete_branch, name='delete_branch'),

    # Classrooms
    path('branches/<str:branch_id>/classrooms/', views.list_classrooms, name='list_classrooms'),
    path('branches/<str:branch_id>/classrooms/create/', views.create_classroom, name='create_classroom'),
    path('classrooms/<str:classroom_id>/', views.view_classroom, name='view_classroom'),
    path('classrooms/<str:classroom_id>/update/', views.update_classroom, name='update_classroom'),
    path('classrooms/<str:classroom_id>/delete/', views.delete_classroom, name='delete_classroom'),
]

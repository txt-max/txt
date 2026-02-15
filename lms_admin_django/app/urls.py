from django.urls import path
from . import views

app_name = 'app'

urlpatterns = [

# Добавьте эту строку в начало списка
    path('', views.dashboard_view, name='home'),


    # Dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),

    # Users
    path('users/', views.users_list_view, name='users_list'),
    path('users/create/', views.users_create_view, name='users_create'),
    path('users/<int:user_id>/edit/', views.users_edit_view, name='users_edit'),
    path('users/<int:user_id>/delete/', views.users_delete_view, name='users_delete'),

    # Courses
    path('courses/', views.courses_list_view, name='courses_list'),
    path('courses/create/', views.courses_create_view, name='courses_create'),
    path('courses/<int:course_id>/', views.courses_detail_view, name='courses_detail'),

    # Groups
    path('groups/', views.groups_list_view, name='groups_list'),

    # Reports
    path('reports/', views.reports_view, name='reports'),

    # Audit
    path('audit/', views.audit_log_view, name='audit_log'),
]
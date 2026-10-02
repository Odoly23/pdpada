from django.contrib.auth.views import LogoutView
from django.urls import path

from users import views

urlpatterns = [
    path('login/', views.PdpadaLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('password/', views.password_change, name='password_change'),
    path('users/', views.user_list, name='user-list'),
    path('users/new/', views.user_create, name='user-create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user-edit'),
    path('users/<int:pk>/reset-password/', views.user_reset_password, name='user-reset-password'),
    path('users/<int:pk>/toggle-active/', views.user_toggle_active, name='user-toggle-active'),
    path('users/<int:pk>/unlock/', views.user_unlock, name='user-unlock'),
    path('audit/', views.audit_list, name='audit-list'),
]

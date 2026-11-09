from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

urlpatterns = [
	path('', views.home, name='home'),
	path('robots.txt', views.robots_txt, name='robots-txt'),
	path('healthz/', views.healthz, name='healthz'),
	path('login/', views.ThrottledLoginView.as_view(), name='login'),
	path('logout/', auth_views.LogoutView.as_view(), name='logout'),
	path('password/', auth_views.PasswordChangeView.as_view(
		template_name='auth/change_password.html', success_url='/password/done/'), name='change-password'),
	path('password/done/', auth_views.PasswordChangeDoneView.as_view(
		template_name='auth/change_password_done.html'), name='password_change_done'),
]

from django.urls import path
from . import views

urlpatterns = [
	path('', views.UserList, name='user-list'),
	path('painel/', views.UserPainel, name='user-painel'),
	path('add/', views.UserAdd, name='user-add'),
	path('<int:pk>/edit/', views.UserUpdate, name='user-update'),
]

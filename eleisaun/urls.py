from django.urls import path
from . import views

urlpatterns = [
	path('live/', views.LiveDashboard, name='eleisaun-live'),
	path('live/data/', views.LiveData, name='eleisaun-live-data'),
	path('komparasaun/', views.Komparasaun, name='eleisaun-komparasaun'),
	path('input/', views.ResultadoInput, name='eleisaun-input'),
	path('resultado/<int:pk>/file/<str:kind>/', views.ResultadoFile, name='eleisaun-file'),
	path('admin/', views.EleisaunAdmin, name='eleisaun-admin'),
	path('admin/eleisaun/add/', views.EleisaunAdd, name='eleisaun-add'),
	path('admin/eleisaun/<int:pk>/live/', views.EleisaunToggle, name='eleisaun-toggle'),
	path('admin/tempat/add/', views.TempatAdd, name='tempat-add'),
	path('admin/fiskais/add/', views.FiskaisAdd, name='fiskais-add'),
	path('admin/fiskais/<int:pk>/del/', views.FiskaisDel, name='fiskais-del'),
	path('admin/resultado/<int:pk>/loke/', views.ResultadoLoke, name='resultado-loke'),
]

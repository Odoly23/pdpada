from django.urls import path
from . import views

urlpatterns = [
	path('', views.MembroList, name='membro-list'),
	path('add/', views.MembroAdd, name='membro-add'),
	path('aprovasaun/', views.AprovasaunList, name='aprovasaun-list'),
	path('aprovasaun/bulk/', views.AprovasaunBulk, name='aprovasaun-bulk'),
	path('aprovasaun/<str:hashid>/aprova/', views.AprovasaunAprova, name='aprovasaun-aprova'),
	path('aprovasaun/<str:hashid>/rejeita/', views.AprovasaunRejeita, name='aprovasaun-rejeita'),
	path('alokasaun/', views.AlokasaunList, name='alokasaun-list'),
	path('alokasaun/add/', views.AlokasaunAdd, name='alokasaun-add'),
	path('alokasaun/<int:pk>/edit/', views.AlokasaunUpdate, name='alokasaun-update'),
	path('alokasaun/<int:pk>/del/', views.AlokasaunDel, name='alokasaun-del'),
	path('historia/', views.HistoriaList, name='historia-list'),
	path('<str:hashid>/', views.MembroDetail, name='membro-detail'),
	path('<str:hashid>/edit/', views.MembroUpdate, name='membro-update'),
	path('<str:hashid>/del/', views.MembroDel, name='membro-del'),
]

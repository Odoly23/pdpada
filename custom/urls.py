from django.urls import path
from . import views

urlpatterns = [
	path('ajax/load-posts/', views.load_posts, name='ajax_load_posts'),
	path('ajax/load-villages/', views.load_villages, name='ajax_load_villages'),
	path('ajax/load-aldeias/', views.load_aldeias, name='ajax_load_aldeias'),
	path('master/<str:tipu>/', views.MasterList, name='master-list'),
	path('master/<str:tipu>/add/', views.MasterAdd, name='master-add'),
	path('master/<str:tipu>/<int:pk>/edit/', views.MasterUpdate, name='master-update'),
	path('master/<str:tipu>/<int:pk>/del/', views.MasterDel, name='master-del'),
	path('ano/<int:pk>/aktiva/', views.AnoAktiva, name='ano-aktiva'),
]

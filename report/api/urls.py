from django.urls import path
from . import views

urlpatterns = [
	path('gender/', views.APIGender.as_view(), name='api-gender'),
	path('aprovasaun/', views.APIAprovasaun.as_view(), name='api-aprovasaun'),
	path('suku/', views.APISuku.as_view(), name='api-suku'),
	path('aldeia/', views.APIAldeia.as_view(), name='api-aldeia'),
	path('status/', views.APIStatus.as_view(), name='api-status'),
	path('marital/', views.APIMarital.as_view(), name='api-marital'),
	path('hakbit/', views.APIHakbit.as_view(), name='api-hakbit'),
	path('age/', views.APIAge.as_view(), name='api-age'),
	path('organizasaun/', views.APIOrganizasaun.as_view(), name='api-organizasaun'),
]

from django.urls import include, path
from . import views

urlpatterns = [
	path('', views.Dash, name='report-dash'),
	path('api/', include('report.api.urls')),
]

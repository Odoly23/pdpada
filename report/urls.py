from django.urls import include, path
from . import views

urlpatterns = [
	path('', views.Dash, name='report-dash'),
	path('chart/', views.ChartDash, name='report-chart'),
	path('api/', include('report.api.urls')),
]

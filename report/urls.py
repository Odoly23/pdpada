from django.urls import include, path

from report import views

urlpatterns = [
    path('', views.dashboard, name='report-dash'),
    path('api/', include('report.api.urls')),
]

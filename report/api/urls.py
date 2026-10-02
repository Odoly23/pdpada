from django.urls import path

from report.api import views

urlpatterns = [path('membru-sumariu/', views.APIMembruSumariu.as_view(), name='api-membru-sumariu')]

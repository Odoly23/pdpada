from django.urls import path
from . import views

urlpatterns = [
	path('badge/', views.APINotifBadge.as_view(), name='api-notif-badge'),
	path('aprovasaun/', views.APINotifPendente.as_view(), name='api-notif-pendente'),
	path('rejeitadu/', views.APINotifRejeitadu.as_view(), name='api-notif-rejeitadu'),
]

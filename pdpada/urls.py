import os

from django.contrib import admin
from django.urls import include, path

ADMIN_URL = os.getenv('ADMIN_URL', 'admin-pdpada/').strip('/') + '/'

urlpatterns = [
    path(ADMIN_URL, admin.site.urls),
    path('', include('main.urls')),
    path('', include('users.urls')),
    path('membru/', include('membro.urls')),
    path('relatoriu/', include('report.urls')),
]

handler403 = 'main.views.error_403'
handler404 = 'main.views.error_404'
handler500 = 'main.views.error_500'

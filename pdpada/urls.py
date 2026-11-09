from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

handler403 = 'main.views.error_403'
handler404 = 'main.views.error_404'
handler500 = 'main.views.error_500'

urlpatterns = [
	path('admin/', admin.site.urls),
	path('', include('main.urls')),
	path('custom/', include('custom.urls')),
	path('users/', include('users.urls')),
	path('membro/', include('membro.urls')),
	path('report/', include('report.urls')),
]

if settings.DEBUG:
	urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

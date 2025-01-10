from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),  # Keep only one instance of admin URLs
    path('accounts/', include('mainapp.urls')),  # Includes the 'mainapp' URLs
    path("", include("mainapp.urls")),  # Include the 'mainapp' URLs for the root path
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])



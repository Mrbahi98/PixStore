from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns

# Main URL configuration
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # Language switcher
]

# Admin (no language prefix)
urlpatterns += [
    path('admin/', admin.site.urls),
]

# App URLs (with language prefixes)
urlpatterns += i18n_patterns(
    path('', include('store.urls')),
)

# Static / media during debug
if settings.DEBUG:
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

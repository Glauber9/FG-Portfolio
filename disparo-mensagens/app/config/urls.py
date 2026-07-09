import importlib.util
from two_factor import urls as two_factor_urls
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include(two_factor_urls.urlpatterns)),
    path('contatos/', include('contatos.urls')),
    path('campanhas/', include('campanhas.urls')),
    path('envios/', include('envios.urls')),
    path('i18n/', include('django.conf.urls.i18n')),
]
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
)
has_debug_toolbar = settings.DEBUG and importlib.util.find_spec('debug_toolbar') is not None

if has_debug_toolbar:
    urlpatterns += [
        path('__debug__/', include('debug_toolbar.urls')),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
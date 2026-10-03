from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),

    # API Schema & Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(), name='redoc'),

    #App Routes
    path('api/auth/', include('apps.users.urls')),
    path('api/investments/', include('apps.investments.urls')),
    path('api/withdrawals/', include('apps.withdrawals.urls')),
    path('api/notifications/', include('apps.notifications.urls')),
    path('api/admin/', include('apps.admin_api.urls')),
    path('api/support/', include('apps.support.urls')),
]

if settings.DEBUG:
   urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
   urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
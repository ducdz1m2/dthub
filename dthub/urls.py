from django.contrib import admin
from django.urls import include, path
from django.conf.urls.static import static
from dthub import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path("forum/", include("forum.urls")),
    path("products/", include("products.urls")),
    path("orders/", include("orders.urls")),
    path("ai/", include("ai_hub.urls")),
    path("accounts/", include("accounts.urls")),
    path("chat/", include("chat.urls")),
    path("", include("dashboard.urls")),
    path('mdeditor/', include('mdeditor.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
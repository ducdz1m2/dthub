from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path("forum/", include("forum.urls")),
    path("products/", include("products.urls")),
    path("orders/", include("orders.urls")),
    path("ai/", include("ai_hub.urls")),
    path("account/", include("accounts.urls")),

]

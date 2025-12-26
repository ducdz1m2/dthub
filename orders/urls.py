from django.urls import path
from . import views


urlpatterns = [
    path("manage/", views.order_manage_view),
]

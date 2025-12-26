from django.urls import path
from . import views

urlpatterns = [
    path("manage/", views.product_manage_view),
]

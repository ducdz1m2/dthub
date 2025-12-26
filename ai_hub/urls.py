from django.urls import path
from . import views

urlpatterns = [
    path("manage/", views.ai_arch_view),
]

from django.urls import path
from . import views

urlpatterns = [
    path("public/", views.forum_public_view),
    path("manage/post/", views.forum_manage_post),
    path("manage/feedback/", views.forum_manage_feedback),
]

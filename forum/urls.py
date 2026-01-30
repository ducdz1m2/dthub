from django.urls import path
from . import views
from . import views_image

app_name = 'forum'

urlpatterns = [
    # Main Forum Views
    path('', views.ForumHomeView.as_view(), name='home'),
    
    # Post CRUD
    path('post/create/', views.PostCreateView.as_view(), name='post_create'),
    path('post/<slug:slug>/', views.PostDetailView.as_view(), name='post_detail'),
    path('post/<slug:slug>/edit/', views.PostUpdateView.as_view(), name='post_update'),
    path('post/<slug:slug>/delete/', views.PostDeleteView.as_view(), name='post_delete'),
    path('delete/<slug:slug>/', views.delete_post_ajax, name='delete_post_ajax'),
    
    # Comments
    path('post/<slug:slug>/comment/', views.add_comment, name='add_comment'),
    
    # Admin Functions
    path('post/<slug:slug>/pin/', views.pin_post, name='pin_post'),
    path('post/<slug:slug>/lock/', views.lock_post, name='lock_post'),
    path('manage/posts/', views.manage_posts, name='manage_posts'),
    path('manage/comments/', views.manage_comments, name='manage_comments'),
    
    # Anonymous Image Serving
    path('image/<str:clean_filename>/', views_image.serve_anonymous_image, name='serve_anonymous_image'),
]

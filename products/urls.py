from django.urls import path
from . import views

urlpatterns = [
    # User
    path("", views.product_list, name="product_list"),
    path("product/<slug:slug>/", views.product_detail, name="product_detail"),
    
    path('order/create/<int:product_id>/', views.create_order_direct, name='create_order_direct'),
    
    # Admin / Staff
    path("admin/create/", views.product_create, name="product_create"),
    path("admin/<int:pk>/edit/", views.product_update, name="product_edit"),
    path("admin/<int:pk>/delete/", views.product_delete, name="product_delete"),
]
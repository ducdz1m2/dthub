from django.urls import path
from . import views

urlpatterns = [
    # Public URLs
    path('', views.firmware_home, name='firmware_home'),
    path('<int:firmware_id>/', views.firmware_detail, name='firmware_detail'),
    path('<int:firmware_id>/manifest.json', views.get_manifest, name='get_manifest'),
    path('<int:firmware_id>/log/', views.log_flashing_session, name='log_flashing_session'),
    
    # Admin Management URLs
    path('manage/', views.firmware_manage, name='firmware_manage'),
    path('create/', views.firmware_create, name='firmware_create'),
    path('edit/<int:firmware_id>/', views.firmware_edit, name='firmware_edit'),
    path('delete/<int:firmware_id>/', views.firmware_delete, name='firmware_delete'),
    path('stats/', views.firmware_stats, name='firmware_stats'),
]

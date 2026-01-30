from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.create_support_request, name='create_support_request'),
    path('my-requests/', views.my_support_requests, name='my_support_requests'),
    path('detail/<int:request_id>/', views.support_request_detail, name='support_request_detail'),
    path('manage/', views.support_manage_view, name='support_manage_view'),
    path('assign/<int:request_id>/', views.assign_support_staff, name='assign_support_staff'),
    path('update-status/<int:request_id>/', views.update_support_status, name='update_support_status'),
]

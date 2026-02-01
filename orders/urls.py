from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('manage/', views.order_manage_view, name='order_manage_view'),
    path('assign/<int:order_id>/', views.assign_technician, name='assign_technician'),
    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('buy/<int:product_id>/', views.create_order_direct, name='create_order_direct'),
    path('staff/dashboard/', views.tech_dashboard, name='tech_dashboard'),
    path('staff/order/<int:order_id>/update/', views.update_job_status, name='update_job_status'),
    path('order/<int:order_id>/review/', views.submit_review, name='submit_review'),
    path('order/<int:order_id>/delete-review/', views.delete_review, name='delete_review'),
]
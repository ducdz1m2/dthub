from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('manage/', views.order_manage_view, name='order_manage_view'),
    path('assign/<int:order_id>/', views.assign_technician, name='assign_technician'),
    path('update-status/<int:order_id>/', views.update_order_status, name='update_order_status'),
    path('delete/<int:order_id>/', views.delete_order, name='delete_order'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('cancel/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('buy/<int:product_id>/', views.create_order_direct, name='create_order_direct'),
    path('staff/dashboard/', views.tech_dashboard, name='tech_dashboard'),
    path('staff/order/<int:order_id>/update/', views.update_job_status, name='update_job_status'),
    path('order/<int:order_id>/review/', views.submit_review, name='submit_review'),
    path('order/<int:order_id>/delete-review/', views.delete_review, name='delete_review'),
    
    # Payment URLs
    path('payment/<int:order_id>/', views.create_payment, name='create_payment'),
    path('payment/detail/<uuid:payment_id>/', views.payment_detail, name='payment_detail'),
    path('payment/success/<uuid:payment_id>/', views.payment_success, name='payment_success'),
    path('payment/failed/<uuid:payment_id>/', views.payment_failed, name='payment_failed'),
    path('vnpay/return/', views.vnpay_return, name='vnpay_return'),
    path('vnpay/ipn/', views.vnpay_ipn, name='vnpay_ipn'),
]
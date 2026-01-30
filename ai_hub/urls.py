from django.urls import path
from . import views

urlpatterns = [
    path("manage/", views.ai_arch_view, name="ai_arch_view"),
    path("", views.dashboard_view, name="ai_dashboard"),
    path("chat/", views.chat_interface, name="ai_chat"),
    path("devices/", views.device_management, name="device_management"),
    path("devices/<str:device_id>/command/", views.send_device_command, name="send_device_command"),
    path("sensors/", views.sensor_data_view, name="sensor_data"),
    path("sensors/<str:device_id>/", views.sensor_data_view, name="device_sensor_data"),
    path("mqtt/webhook/", views.mqtt_webhook, name="mqtt_webhook"),
]

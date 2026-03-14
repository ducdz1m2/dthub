from django.urls import path
from . import views
from . import mcp_views
from . import mcp_builtin_views
from . import device_api
from . import esp32_api

urlpatterns = [
    path("", views.dashboard_view, name="ai_dashboard"),
    path("chat/", views.chat_interface, name="ai_chat"),
    path("chat/history/clear/", views.clear_chat_history, name="clear_all_chat_history"),
    path("chat/history/clear/<str:session_id>/", views.clear_chat_history, name="clear_chat_history"),
    path("chat/history/<str:session_id>/", views.get_chat_history_api, name="get_chat_history"),
    path("voice/", views.voice_chat, name="voice_chat"),
    path("devices/", views.device_management, name="device_management"),
    path("devices/<str:device_id>/", views.device_detail, name="device_detail"),
    path("devices/<str:device_id>/delete/", views.delete_device, name="delete_device"),
    path("devices/<str:device_id>/label/add/", views.add_device_label, name="add_device_label"),
    path("devices/label/<int:pk>/delete/", views.delete_device_label, name="delete_device_label"),
    path("devices/<str:device_id>/command/", views.send_device_command, name="send_device_command"),
    path("sensors/", views.sensor_data_view, name="sensor_data"),
    path("sensors/<str:device_id>/", views.sensor_data_view, name="device_sensor_data"),
    path("sensors/clear/all/", views.delete_sensor_data, name="clear_all_sensor_data"),
    path("sensors/clear/<str:device_id>/", views.delete_sensor_data, name="clear_device_sensor_data"),
    path("mqtt/webhook/", views.mqtt_webhook, name="mqtt_webhook"),
    
    # AI Configuration Management
    path("config/", views.ai_config_list, name="ai_config_list"),
    path("config/create/", views.ai_config_create, name="ai_config_create"),
    path("config/<int:pk>/edit/", views.ai_config_edit, name="ai_config_edit"),
    path("config/<int:pk>/delete/", views.ai_config_delete, name="ai_config_delete"),
    path("config/<int:pk>/set-default/", views.ai_config_set_default, name="ai_config_set_default"),
    # AI Configuration API
    path("config/active/", views.get_active_ai_config, name="get_active_ai_config"),
    
    # Dynamic MCP Tools API
    path("api/tools/", views.api_mcp_tools, name="api_mcp_tools"),
    
    # MCP Tools Management (User-based)
    path("mcp/public-tools/", views.mcp_public_tools, name="mcp_public_tools"),
    path("mcp/my-tools/", views.mcp_my_tools, name="mcp_my_tools"),
    path("mcp/tools/<str:tool_name>/add/", views.mcp_tool_add, name="mcp_tool_add"),
    path("mcp/tools/<str:tool_name>/remove/", views.mcp_tool_remove, name="mcp_tool_remove"),
    
    # MCP Server Management (chung)
    path("mcp/", mcp_views.mcp_dashboard, name="mcp_dashboard"),
    path("mcp/create/", views.create_mcp_server, name="create_mcp_server"),
    path("mcp/server/<str:device_id>/", mcp_views.mcp_server_detail, name="mcp_server_detail"),
    path("mcp/editor/<int:pk>/", mcp_views.mcp_server_editor, name="mcp_server_editor"),
    path("mcp/editor/<int:pk>/save/", mcp_views.mcp_save_code, name="mcp_save_code"),
    path("mcp/editor/<int:pk>/test/", mcp_views.mcp_test_code, name="mcp_test_code"),
    path("mcp/sync/<int:pk>/", mcp_views.mcp_sync_tools, name="mcp_sync_tools"),
    path("mcp/register/", mcp_views.mcp_register_server, name="mcp_register_server"),
    path("mcp/auto-register/", mcp_views.mcp_auto_register, name="mcp_auto_register"),
    path("mcp/unregister/<str:device_id>/", mcp_views.mcp_unregister_server, name="mcp_unregister_server"),
    path("mcp/call/<str:device_id>/", mcp_views.mcp_call_tool, name="mcp_call_tool"),
    path("mcp/refresh/<str:device_id>/", mcp_views.mcp_refresh_server, name="mcp_refresh_server"),
    path("mcp/health/", mcp_views.mcp_health_check, name="mcp_health_check"),
    
    # MCP Device Endpoints (no authentication required)
    path("mcp/device-register/", device_api.mcp_device_register, name="mcp_device_register"),
    path("mcp/device-heartbeat/", device_api.mcp_device_heartbeat, name="mcp_device_heartbeat"),
    path("mcp/heartbeat/", mcp_views.mcp_heartbeat, name="mcp_heartbeat"),
    path("mcp/discover/", mcp_views.mcp_discover_servers, name="mcp_discover_servers"),
    path("mcp/resources/<str:device_id>/", mcp_views.mcp_server_resources, name="mcp_server_resources"),
    path("mcp/tools/<str:device_id>/", mcp_views.mcp_server_tools, name="mcp_server_tools"),
    path("mcp/batch/", mcp_views.mcp_batch_operation, name="mcp_batch_operation"),

    path("mcp/builtin/<str:kind>/<str:device_id>/info", mcp_builtin_views.builtin_info, name="builtin_mcp_info_plain"),
    path("mcp/builtin/<str:kind>/<str:device_id>/mcp/info", mcp_builtin_views.builtin_mcp_info, name="builtin_mcp_info"),
    path("mcp/builtin/<str:kind>/<str:device_id>/mcp/tools", mcp_builtin_views.builtin_mcp_tools, name="builtin_mcp_tools"),
    path("mcp/builtin/<str:kind>/<str:device_id>/mcp/resources", mcp_builtin_views.builtin_mcp_resources, name="builtin_mcp_resources"),
    path("mcp/builtin/<str:kind>/<str:device_id>/mcp/call", mcp_builtin_views.builtin_mcp_call, name="builtin_mcp_call"),
    
    # ESP32 AI API (Hybrid Session)
    path("api/esp32/handshake/", esp32_api.esp32_session_handshake, name="esp32_handshake"),
    path("api/esp32/interact/", esp32_api.esp32_interact, name="esp32_interact"),
    
    # HTTP Device API (Token-based Authentication) - REMOVED OLD FUNCTIONS
    # path("api/device/register/", device_api.device_register_http, name="device_register_http"),
    # path("api/device/sensor-data/", device_api.device_sensor_data, name="device_sensor_data"),
    # path("api/device/status/", device_api.device_status, name="device_status"),
    # path("api/device/heartbeat/", device_api.device_heartbeat, name="device_heartbeat"),
    # path("api/device/commands/", device_api.device_commands, name="device_commands"),
    # path("api/device/command-result/", device_api.device_command_result, name="device_command_result"),
]

from django.urls import path
from . import views
from . import mcp_views
from . import esp32_api

urlpatterns = [

    # ── Dashboard ────────────────────────────────────────────────────────────
    path("", views.dashboard_view, name="ai_dashboard"),

    # ── Chat ─────────────────────────────────────────────────────────────────
    path("chat/", views.chat_interface, name="ai_chat"),
    path("chat/history/clear/", views.clear_chat_history, name="clear_all_chat_history"),
    path("chat/history/clear/<str:session_id>/", views.clear_chat_history, name="clear_chat_history"),
    path("chat/history/<str:session_id>/", views.get_chat_history_api, name="get_chat_history"),

    # ── Devices ──────────────────────────────────────────────────────────────
    path("devices/", views.device_management, name="device_management"),
    path("devices/label/<int:pk>/delete/", views.delete_device_label, name="delete_device_label"),
    path("devices/<str:device_id>/", views.device_detail, name="device_detail"),
    path("devices/<str:device_id>/delete/", views.delete_device, name="delete_device"),
    path("devices/<str:device_id>/label/add/", views.add_device_label, name="add_device_label"),
    path("devices/<str:device_id>/command/", views.send_device_command, name="send_device_command"),
    path("devices/<str:device_id>/ping/", views.ping_device, name="ping_device"),

    # ── Sensors ──────────────────────────────────────────────────────────────
    path("sensors/", views.sensor_data_view, name="sensor_data"),
    path("sensors/clear/all/", views.delete_sensor_data, name="clear_all_sensor_data"),
    path("sensors/clear/<str:device_id>/", views.delete_sensor_data, name="clear_device_sensor_data"),
    path("sensors/<str:device_id>/", views.sensor_data_view, name="device_sensor_data"),

    # ── AI Config ────────────────────────────────────────────────────────────
    path("config/", views.ai_config_list, name="ai_config_list"),
    path("config/create/", views.ai_config_create, name="ai_config_create"),
    path("config/<int:pk>/edit/", views.ai_config_edit, name="ai_config_edit"),
    path("config/<int:pk>/delete/", views.ai_config_delete, name="ai_config_delete"),
    path("config/<int:pk>/set-default/", views.ai_config_set_default, name="ai_config_set_default"),
    path("config/active/", views.get_active_ai_config, name="get_active_ai_config"),

    # STT/LLM/TTS sub-configs được chỉnh sửa inline qua ai_config_edit, không cần expose riêng

    # ── Tools (public browse + user add/remove) ───────────────────────────────
    path("tools/", views.mcp_public_tools, name="mcp_public_tools"),
    path("tools/<str:tool_name>/add/", views.mcp_tool_add, name="mcp_tool_add"),
    path("tools/<str:tool_name>/remove/", views.mcp_tool_remove, name="mcp_tool_remove"),

    # ── Knowledge Base ────────────────────────────────────────────────────────
    # User: thêm/gỡ KB
    path("kb/<int:kb_id>/add/", views.kb_add, name="kb_add"),
    path("kb/<int:kb_id>/remove/", views.kb_remove, name="kb_remove"),
    path("kb/user/list/", views.kb_user_list_api, name="kb_user_list_api"),
    # Admin: CRUD + upload
    path("kb/", views.kb_list, name="kb_list"),
    path("kb/create/", views.kb_create, name="kb_create"),
    path("kb/<int:kb_id>/edit/", views.kb_edit, name="kb_edit"),
    path("kb/<int:kb_id>/delete/", views.kb_delete, name="kb_delete"),
    path("kb/<int:kb_id>/upload/", views.kb_upload_document, name="kb_upload_document"),
    path("kb/<int:kb_id>/documents/", views.kb_documents, name="kb_documents"),
    path("kb/<int:kb_id>/documents/delete/", views.kb_delete_document, name="kb_delete_document"),
    path("kb/<int:kb_id>/clear/", views.kb_clear_namespace, name="kb_clear_namespace"),
    path("kb/<int:kb_id>/info/", views.kb_info, name="kb_info"),

    # ── MCP Server Management (admin) ─────────────────────────────────────────
    path("mcp/", mcp_views.mcp_dashboard, name="mcp_dashboard"),
    path("mcp/create/", views.create_mcp_server, name="create_mcp_server"),
    path("mcp/register/", mcp_views.mcp_register_server, name="mcp_register_server"),
    path("mcp/auto-register/", mcp_views.mcp_auto_register, name="mcp_auto_register"),
    path("mcp/health/", mcp_views.mcp_health_check, name="mcp_health_check"),
    path("mcp/discover/", mcp_views.mcp_discover_servers, name="mcp_discover_servers"),
    path("mcp/batch/", mcp_views.mcp_batch_operation, name="mcp_batch_operation"),
    path("mcp/server/<str:device_id>/", mcp_views.mcp_server_detail, name="mcp_server_detail"),
    path("mcp/server/<str:device_id>/tools/", mcp_views.mcp_server_tools, name="mcp_server_tools"),
    path("mcp/server/<str:device_id>/resources/", mcp_views.mcp_server_resources, name="mcp_server_resources"),
    path("mcp/server/<str:device_id>/call/", mcp_views.mcp_call_tool, name="mcp_call_tool"),
    path("mcp/server/<str:device_id>/refresh/", mcp_views.mcp_refresh_server, name="mcp_refresh_server"),
    path("mcp/server/<str:device_id>/sync/", mcp_views.mcp_sync_by_device_id, name="mcp_sync_by_device_id"),
    path("mcp/server/<str:device_id>/toggle/", mcp_views.mcp_toggle_server, name="mcp_toggle_server"),
    path("mcp/server/<str:device_id>/unregister/", mcp_views.mcp_unregister_server, name="mcp_unregister_server"),
    path("mcp/editor/<int:pk>/", mcp_views.mcp_server_editor, name="mcp_server_editor"),
    path("mcp/editor/<int:pk>/save/", mcp_views.mcp_save_code, name="mcp_save_code"),
    path("mcp/editor/<int:pk>/test/", mcp_views.mcp_test_code, name="mcp_test_code"),
    path("mcp/editor/<int:pk>/sync/", mcp_views.mcp_sync_tools, name="mcp_sync_tools"),
    # ── Internal API ──────────────────────────────────────────────────────────
    path("api/tools/", views.api_mcp_tools, name="api_mcp_tools"),
    path("api/tools/device-control/", views.api_device_control, name="api_device_control"),
    path("api/tools/list-devices/", views.api_list_devices, name="api_list_devices"),
    path("api/tools/user-info/", views.api_user_info, name="api_user_info"),
    path("api/tools/list-products/", views.api_list_products, name="api_list_products"),
    path("api/tools/order-status/", views.api_order_status, name="api_order_status"),
    # ESP32 API
    path("api/esp32/handshake/", esp32_api.esp32_session_handshake, name="esp32_handshake"),
    path("api/esp32/interact/", esp32_api.esp32_interact, name="esp32_interact"),

    # ── Speech Service proxy ──────────────────────────────────────────────────
    path("speech/stt/", views.speech_stt_proxy, name="speech_stt"),
    path("speech/tts/", views.speech_tts_proxy, name="speech_tts"),

    # ── RAG (user personal documents) ────────────────────────────────────────
    path("rag/documents/list/", views.rag_document_list_api, name="rag_document_list"),
    path("rag/documents/upload/", views.rag_document_upload, name="rag_document_upload"),
    path("rag/documents/<int:doc_id>/delete/", views.rag_document_delete, name="rag_document_delete"),
    path("rag/documents/reindex/", views.rag_reindex, name="rag_reindex"),
]

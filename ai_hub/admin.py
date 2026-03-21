from django.contrib import admin
from .models import ESP32Device, SensorData, DeviceCommand, ChatSession, ChatMessage, LLMConfiguration


@admin.register(ESP32Device)
class ESP32DeviceAdmin(admin.ModelAdmin):
    list_display = ('device_id', 'name', 'device_type', 'ip_address', 'location', 'is_active', 'last_seen')
    list_filter = ('device_type', 'is_active', 'created_at')
    search_fields = ('device_id', 'name', 'location')
    readonly_fields = ('created_at', 'last_seen')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('device_id', 'name', 'device_type')
        }),
        ('Network', {
            'fields': ('ip_address',)
        }),
        ('Status', {
            'fields': ('location', 'is_active', 'last_seen')
        }),
    )


@admin.register(SensorData)
class SensorDataAdmin(admin.ModelAdmin):
    list_display = ('device', 'sensor_type', 'value', 'unit', 'timestamp')
    list_filter = ('sensor_type', 'timestamp', 'device')
    search_fields = ('device__name', 'device__device_id')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('device')


@admin.register(DeviceCommand)
class DeviceCommandAdmin(admin.ModelAdmin):
    list_display = ('device', 'command', 'status', 'created_at', 'executed_at')
    list_filter = ('status', 'command', 'created_at')
    search_fields = ('device__name', 'device__device_id', 'command')
    readonly_fields = ('created_at', 'executed_at')
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('device')


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('session_id', 'user', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('session_id', 'user__username')
    readonly_fields = ('session_id', 'created_at')
    ordering = ('-created_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'tool_used', 'response_time', 'timestamp')
    list_filter = ('tool_used', 'timestamp')
    search_fields = ('session__session_id', 'query', 'response')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('session')


@admin.register(LLMConfiguration)
class LLMConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'model', 'router_model', 'router_timeout', 'is_active']
    fieldsets = (
        ('Model Configuration', {
            'fields': ('name', 'model', 'temperature', 'max_tokens', 'response_language', 'system_prompt', 'is_active')
        }),
        ('Router Configuration', {
            'fields': ('router_model', 'router_timeout')
        }),
    )

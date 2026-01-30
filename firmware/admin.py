from django.contrib import admin
from .models import FirmwareFile, FlashingSession

@admin.register(FirmwareFile)
class FirmwareFileAdmin(admin.ModelAdmin):
    list_display = ['name', 'device_type', 'version', 'is_active', 'created_at', 'flash_count']
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = ['name', 'version', 'description']
    readonly_fields = ['created_at', 'updated_at', 'flash_count']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('name', 'device_type', 'version', 'is_active')
        }),
        ('Nội dung', {
            'fields': ('description',)
        }),
        ('Files', {
            'fields': ('bin_file', 'manifest_file')
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def flash_count(self, obj):
        return obj.flashing_sessions.count()
    flash_count.short_description = 'Số lần nạp'

@admin.register(FlashingSession)
class FlashingSessionAdmin(admin.ModelAdmin):
    list_display = ['firmware', 'user_ip', 'success', 'flashed_at', 'error_message_short']
    list_filter = ['success', 'flashed_at', 'firmware']
    search_fields = ['firmware__name', 'user_ip', 'error_message']
    readonly_fields = ['flashed_at', 'user_ip', 'user_agent']
    ordering = ['-flashed_at']
    
    fieldsets = (
        ('Thông tin session', {
            'fields': ('firmware', 'success', 'flashed_at')
        }),
        ('Thông tin người dùng', {
            'fields': ('user_ip', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Lỗi', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        })
    )
    
    def error_message_short(self, obj):
        return obj.error_message[:50] + '...' if obj.error_message and len(obj.error_message) > 50 else obj.error_message
    error_message_short.short_description = 'Lỗi'

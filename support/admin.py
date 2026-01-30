from django.contrib import admin
from .models import SupportRequest, SupportResponse, SupportAttachment

@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'category', 'priority', 'status', 'assigned_to', 'created_at']
    list_filter = ['status', 'priority', 'category', 'created_at']
    search_fields = ['title', 'user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Thông tin cơ bản', {
            'fields': ('user', 'title', 'category', 'priority', 'status')
        }),
        ('Nội dung', {
            'fields': ('description',)
        }),
        ('Phân công', {
            'fields': ('assigned_to',)
        }),
        ('Thời gian', {
            'fields': ('created_at', 'updated_at', 'resolved_at'),
            'classes': ('collapse',)
        })
    )

@admin.register(SupportResponse)
class SupportResponseAdmin(admin.ModelAdmin):
    list_display = ['support_request', 'author', 'created_at', 'content_preview']
    list_filter = ['created_at']
    search_fields = ['support_request__title', 'author__username', 'content']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Nội dung'

@admin.register(SupportAttachment)
class SupportAttachmentAdmin(admin.ModelAdmin):
    list_display = ['support_request', 'filename', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['filename', 'support_request__title']
    readonly_fields = ['uploaded_at']
    ordering = ['-uploaded_at']

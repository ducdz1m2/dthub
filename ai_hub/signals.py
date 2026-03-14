"""
Signals for ai_hub app - Auto-assign default tools to new users
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

User = get_user_model()


@receiver(post_save, sender=User)
def assign_default_tools_to_new_user(sender, instance, created, **kwargs):
    """Automatically assign default MCP tools to newly created users"""
    if created:
        try:
            from .models import MCPTool, UserMCPTool
            
            # Get all enabled tools
            default_tools = MCPTool.objects.filter(is_enabled=True)
            
            # Create UserMCPTool for each default tool
            for tool in default_tools:
                UserMCPTool.objects.get_or_create(
                    user=instance,
                    tool=tool,
                    defaults={'is_active': True}
                )
            
            print(f"[SIGNAL] Assigned {default_tools.count()} default tools to new user: {instance.username}")
        except Exception as e:
            print(f"[SIGNAL ERROR] Failed to assign default tools: {e}")

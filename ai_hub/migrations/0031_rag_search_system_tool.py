"""Đảm bảo rag_search là system tool (luôn available cho mọi user)."""
from django.db import migrations


def set_rag_search_system(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    MCPTool.objects.filter(name='rag_search').update(is_system=True, is_enabled=True)


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0030_userdocument'),
    ]

    operations = [
        migrations.RunPython(set_rag_search_system, migrations.RunPython.noop),
    ]

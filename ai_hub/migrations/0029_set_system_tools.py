from django.db import migrations

# Các tool cơ bản mặc định cho mọi user mới
SYSTEM_TOOL_NAMES = [
    'wiki_search',
    'wiki_summary',
    'english_define',
    'japanese_lookup',
    'system_info',
    'weather_info',
    'help_info',
    'tool_metadata',
]


def set_system_tools(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    MCPTool.objects.filter(name__in=SYSTEM_TOOL_NAMES).update(is_system=True)


def unset_system_tools(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    MCPTool.objects.filter(name__in=SYSTEM_TOOL_NAMES).update(is_system=False)


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0028_add_router_fields_to_llmconfiguration'),
    ]

    operations = [
        migrations.RunPython(set_system_tools, unset_system_tools),
    ]

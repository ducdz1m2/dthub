"""
Migration: Unset is_system cho các tool user-controlled.
Chỉ giữ is_system=True cho rag_search, help_info, tool_metadata (luôn available).
Các tool còn lại (wiki_search, english_define, v.v.) phải được user tự thêm vào collection.
"""
from django.db import migrations

# Các tool thực sự là system — luôn available, không cần user thêm
KEEP_SYSTEM = {'rag_search', 'help_info', 'tool_metadata', 'general_chat', 'no_tool_available'}

# Các tool trước đây bị set is_system=True nhầm — cần unset để permission check hoạt động
UNSET_SYSTEM = [
    'wiki_search',
    'wiki_summary',
    'english_define',
    'japanese_lookup',
    'system_info',
    'weather_info',
    'physics_calculation',
    'chemistry_calculation',
    'lookup_element',
    'molar_mass',
    'balance_equation',
]


def unset_system_tools(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    MCPTool.objects.filter(name__in=UNSET_SYSTEM).update(is_system=False)


def revert_system_tools(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    MCPTool.objects.filter(name__in=UNSET_SYSTEM).update(is_system=True)


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0037_fix_keywords_unicode'),
    ]

    operations = [
        migrations.RunPython(unset_system_tools, revert_system_tools),
    ]

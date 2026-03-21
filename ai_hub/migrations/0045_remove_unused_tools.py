"""
Migration 0045: Xóa các tool không còn dùng khỏi DB.
Bỏ: translate, stats_basic, molar_mass, time_now, unix_time, uuid4, hash_text, base64_encode, base64_decode
"""
from django.db import migrations

REMOVE_TOOLS = [
    'translate', 'stats_basic', 'molar_mass',
    'time_now', 'unix_time', 'uuid4', 'hash_text', 'base64_encode', 'base64_decode',
]


def remove_tools(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    deleted, _ = MCPTool.objects.filter(name__in=REMOVE_TOOLS).delete()
    print(f"  Deleted {deleted} unused tools")


class Migration(migrations.Migration):
    dependencies = [
        ('ai_hub', '0044_drop_router_strategy'),
    ]

    operations = [
        migrations.RunPython(remove_tools, migrations.RunPython.noop),
    ]

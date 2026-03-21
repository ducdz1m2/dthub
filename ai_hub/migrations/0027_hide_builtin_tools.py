from django.db import migrations


BUILTIN_TOOL_NAMES = [
    'wiki_search', 'wiki_summary', 'rag_search',
    'physics_calculation', 'chemistry_calculation',
    'english_define', 'japanese_lookup',
    'system_info', 'weather_info', 'tool_metadata',
    'sensor_read',
]


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0026_mcptool_source_server_online'),
    ]

    operations = [
        # Xóa UserMCPTool liên kết đến các built-in tool này
        migrations.RunSQL(
            sql="""
                DELETE FROM ai_hub_usermcptool
                WHERE tool_id IN (
                    SELECT id FROM ai_hub_mcptool
                    WHERE name IN ({placeholders})
                );
            """.format(placeholders=','.join(f"'{n}'" for n in BUILTIN_TOOL_NAMES)),
            reverse_sql="-- không thể khôi phục UserMCPTool đã xóa",
        ),
        # Ẩn và vô hiệu hóa các built-in tool
        migrations.RunSQL(
            sql="""
                UPDATE ai_hub_mcptool
                SET is_public = FALSE,
                    is_visible = FALSE,
                    is_enabled = FALSE
                WHERE name IN ({placeholders})
                  AND is_system = FALSE;
            """.format(placeholders=','.join(f"'{n}'" for n in BUILTIN_TOOL_NAMES)),
            reverse_sql="""
                UPDATE ai_hub_mcptool
                SET is_public = TRUE,
                    is_visible = TRUE,
                    is_enabled = TRUE
                WHERE name IN ({placeholders})
                  AND is_system = FALSE;
            """.format(placeholders=','.join(f"'{n}'" for n in BUILTIN_TOOL_NAMES)),
        ),
    ]

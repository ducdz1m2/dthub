from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0025_alter_mcpserver_server_type'),
    ]

    operations = [
        # Thêm FK source_server vào MCPTool để biết tool đến từ server nào
        migrations.AddField(
            model_name='mcptool',
            name='source_server',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='discovered_tools',
                to='ai_hub.mcpserver',
                verbose_name='Nguồn server',
                help_text='Server thực sự cung cấp tool này. Null = tool nội bộ (ảo).',
            ),
        ),
        # Đánh dấu tool nội bộ (ảo) không còn public nữa
        migrations.RunSQL(
            sql="""
                UPDATE ai_hub_mcptool
                SET is_public = FALSE, is_visible = FALSE
                WHERE source_server_id IS NULL AND is_system = FALSE;
            """,
            reverse_sql="""
                UPDATE ai_hub_mcptool
                SET is_public = TRUE, is_visible = TRUE
                WHERE source_server_id IS NULL AND is_system = FALSE;
            """,
        ),
    ]

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0043_add_knowledgebase_models'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE ai_hub_llmconfiguration DROP COLUMN IF EXISTS router_strategy",
            reverse_sql="ALTER TABLE ai_hub_llmconfiguration ADD COLUMN router_strategy VARCHAR(50) NOT NULL DEFAULT 'semantic'",
        ),
    ]

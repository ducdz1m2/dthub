# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0006_alter_chatsession_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mcpserver',
            name='domain',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Domain'),
        ),
        migrations.AlterField(
            model_name='mcpserver',
            name='subdomain',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True, verbose_name='Subdomain'),
        ),
    ]

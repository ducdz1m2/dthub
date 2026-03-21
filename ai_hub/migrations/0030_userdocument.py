from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0029_set_system_tools'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=255, verbose_name='Tên file')),
                ('file_type', models.CharField(max_length=10, verbose_name='Loại file')),
                ('file_size', models.IntegerField(verbose_name='Kích thước (bytes)')),
                ('chunk_count', models.IntegerField(default=0, verbose_name='Số chunks')),
                ('status', models.CharField(
                    choices=[('pending', 'Đang xử lý'), ('success', 'Thành công'), ('failed', 'Thất bại')],
                    default='pending', max_length=10, verbose_name='Trạng thái'
                )),
                ('error_message', models.TextField(blank=True, verbose_name='Lỗi')),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'User Document',
                'verbose_name_plural': 'User Documents',
                'ordering': ['-uploaded_at'],
            },
        ),
    ]

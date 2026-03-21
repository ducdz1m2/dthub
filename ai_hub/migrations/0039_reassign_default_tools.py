"""
Migration: Gán lại default tools cho tất cả user hiện có.
Các tool public từ local-mcp-8002 được tự động thêm vào collection của mọi user
nếu họ chưa có.
"""
from django.db import migrations


# Tên base (không prefix) của các tool mặc định
DEFAULT_TOOL_BASE_NAMES = [
    'wiki_search', 'wiki_summary',
    'english_define', 'japanese_lookup', 'translate',
    'calc', 'quadratic', 'stats_basic',
    'ohms_law', 'kinematics_v', 'constants',
    'lookup_element', 'molar_mass', 'balance_equation',
    'device_control', 'list_devices',
    'get_user_info', 'list_products', 'get_order_status',
    'time_now', 'system_info', 'weather_info',
]


def assign_default_tools(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    UserMCPTool = apps.get_model('ai_hub', 'UserMCPTool')
    User = apps.get_model('accounts', 'User')

    # Tìm tất cả tool public/builtin (không phải system) đang enabled
    # Match cả tên có prefix lẫn không prefix
    tools = []
    for base in DEFAULT_TOOL_BASE_NAMES:
        # Tìm theo tên chính xác hoặc tên kết thúc bằng _<base>
        found = MCPTool.objects.filter(is_enabled=True, is_system=False).filter(
            **{'name': base}
        ).first()
        if not found:
            found = MCPTool.objects.filter(is_enabled=True, is_system=False).filter(
                name__endswith=f'_{base}'
            ).first()
        if found:
            tools.append(found)

    if not tools:
        print("  No tools found to assign")
        return

    print(f"  Found {len(tools)} tools to assign")

    for user in User.objects.all():
        created_count = 0
        for tool in tools:
            _, created = UserMCPTool.objects.get_or_create(
                user=user,
                tool=tool,
                defaults={'is_active': True},
            )
            if created:
                created_count += 1
        if created_count:
            print(f"  User {user.username}: assigned {created_count} new tools")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0038_unset_system_for_user_tools'),
    ]

    operations = [
        migrations.RunPython(assign_default_tools, noop),
    ]

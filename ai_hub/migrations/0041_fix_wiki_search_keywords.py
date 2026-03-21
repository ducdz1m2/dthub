"""
Migration 0041: Fix wiki_search keywords — xóa các keyword quá chung
("là gì", "là ai") gây conflict với japanese_lookup/english_define.
wiki_search chỉ nên match khi query rõ ràng hỏi về nhân vật/sự kiện/địa danh.
"""
from django.db import migrations

WIKI_KEYWORDS = [
    # Nhân vật / tổ chức
    "nhân vật", "người nổi tiếng", "nhà khoa học", "nhà phát minh",
    "nhà văn", "nhà thơ", "chính trị gia", "tổng thống", "thủ tướng",
    # Sự kiện / lịch sử
    "lịch sử", "sự kiện", "chiến tranh", "cách mạng", "thế chiến",
    # Khoa học / phát minh
    "khoa học", "phát minh", "khám phá", "lý thuyết", "công thức",
    # Địa danh
    "địa danh", "quốc gia", "thành phố", "châu lục", "đất nước",
    # Wikipedia explicit
    "wikipedia", "wiki",
    # Tìm kiếm thông tin rõ ràng
    "tìm kiếm", "cho tôi biết về", "giới thiệu về", "thông tin về",
    "tiểu sử", "biography", "history",
]


def apply(apps, schema_editor):
    MCPTool = apps.get_model("ai_hub", "MCPTool")
    updated = MCPTool.objects.filter(name="wiki_search").update(keywords=WIKI_KEYWORDS)
    print(f"  Updated wiki_search keywords: {updated} row(s)")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ai_hub", "0040_fix_balance_molar_keywords"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]

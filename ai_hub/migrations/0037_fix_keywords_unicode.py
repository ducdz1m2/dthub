"""
Migration: fix keywords co dau cho japanese_lookup va lookup_element
"""
from django.db import migrations

UPDATES = {
    "japanese_lookup": {
        "keywords": [
            "tiếng nhật", "japanese", "kanji", "hiragana", "katakana",
            "jisho", "tra từ nhật", "nhật bản", "chữ nhật",
            "từ nhật", "nghĩa tiếng nhật", "tra nhật", "từ điển nhật",
            "kimochi", "kawaii", "sakura", "anime", "manga",
            "tìm kiếm từ", "tra cứu từ nhật", "từ này tiếng nhật",
        ],
        "quick_command": "kimochi tiếng Nhật nghĩa là gì?",
    },
    "lookup_element": {
        "keywords": [
            "nguyên tố", "nguyên tố hóa học", "element", "ký hiệu hóa học",
            "bảng tuần hoàn", "bảng hóa học", "bảng nguyên tố",
            "nhôm", "sắt", "đồng", "vàng", "bạc", "kẽ", "chì",
            "oxy", "hydro", "carbon", "natri", "kali", "canxi", "clo",
            "tìm kiếm nguyên tố", "tra cứu nguyên tố",
            "nguyên tử khối", "số hiệu nguyên tử",
            "Al", "Fe", "Cu", "Au", "Ag", "O", "H", "C", "Na", "K", "Ca",
        ],
        "quick_command": "nguyên tố nhôm trong bảng tuần hoàn",
    },
}


def apply(apps, schema_editor):
    MCPTool = apps.get_model("ai_hub", "MCPTool")
    for suffix, data in UPDATES.items():
        tools = MCPTool.objects.filter(name__iendswith=suffix)
        count = tools.update(
            keywords=data["keywords"],
            quick_command=data.get("quick_command", ""),
        )
        print(f"  Updated {count}x: *{suffix}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ai_hub", "0036_fix_japanese_chemistry_keywords"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]

"""
Migration: bo sung keywords cho japanese_lookup va chemistry_lookup
"""
from django.db import migrations

UPDATES = {
    "japanese_lookup": {
        "description": "Tra cuu tu/kanji tieng Nhat qua Jisho.org.",
        "keywords": [
            "tieng nhat", "japanese", "kanji", "hiragana", "katakana",
            "jisho", "tra tu nhat", "nhat ban", "chu nhat",
            "tu nhat", "nghia tieng nhat", "tra nhat", "tu dien nhat",
            "kimochi", "kawaii", "sakura", "anime", "manga",
            "tim kiem tu", "tra cuu tu nhat", "tu nay tieng nhat",
        ],
        "quick_command": "kimochi tieng Nhat nghia la gi?",
    },
    "chemistry_lookup": {
        "description": "Tra cuu nguyen to hoa hoc, phan ung, cong thuc.",
        "keywords": [
            "hoa hoc", "chemistry", "nguyen to", "phan ung", "element",
            "bang tuan hoan", "bang hoa hoc", "bang nguyen to",
            "nhom", "sat", "dong", "vang", "bac", "kem", "chi",
            "oxy", "hydro", "carbon", "natri", "kali", "canxi", "clo",
            "tim kiem nguyen to", "tra cuu nguyen to", "ky hieu hoa hoc",
            "nguyen tu khoi", "so hieu nguyen tu",
        ],
        "quick_command": "nguyen to nhom trong bang tuan hoan",
    },
}


def apply(apps, schema_editor):
    MCPTool = apps.get_model("ai_hub", "MCPTool")
    for name, data in UPDATES.items():
        tools = MCPTool.objects.filter(name__iendswith=name)
        count = tools.update(
            keywords=data["keywords"],
            description=data["description"],
            quick_command=data.get("quick_command", ""),
        )
        print(f"  Updated {count}x: {name}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ai_hub", "0035_fix_chemistry_knowledge_keywords"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]

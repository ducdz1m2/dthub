"""
Migration: fix keywords để tránh nhầm lẫn giữa balance_equation và molar_mass.
- balance_equation: thêm keyword mạnh về cân bằng phương trình
- molar_mass: bỏ ký hiệu hóa học cụ thể (H2O, NaCl) tránh match nhầm
"""
from django.db import migrations

UPDATES = {
    "balance_equation": {
        "keywords": [
            "cân bằng phương trình", "cân bằng hóa học", "balance equation",
            "cân bằng", "phương trình hóa học", "phản ứng hóa học",
            "H2 + O2", "H2 + Cl2", "Fe + O2", "cân bằng phản ứng",
            "hệ số cân bằng", "cân bằng oxi hóa",
        ],
        "quick_command": "cân bằng H2 + O2 = H2O",
    },
    "molar_mass": {
        "keywords": [
            "khối lượng mol", "molar mass", "mol của",
            "tính mol", "phân tử khối", "khối lượng phân tử",
            "g/mol", "tính khối lượng mol",
        ],
        "quick_command": "tính khối lượng mol của H2O",
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
        ("ai_hub", "0039_reassign_default_tools"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]

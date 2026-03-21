"""
Migration: fix keywords for lookup_element (add chemistry-specific terms),
           wiki_search (remove ambiguous "tra cứu"),
           molar_mass (add phân tử khối, tính mol).
"""
from django.db import migrations

UPDATES = {
    "lookup_element": {
        "description": "Tra cứu nguyên tố hóa học: nguyên tử khối, số hiệu nguyên tử, số proton, electron theo ký hiệu (H, O, Na, Fe...) hoặc tên.",
        "keywords": [
            "nguyên tố", "nguyên tố hóa học", "element", "ký hiệu hóa học",
            "nguyên tử khối", "khối lượng nguyên tử", "atomic weight", "atomic mass",
            "số hiệu nguyên tử", "số proton", "số electron", "số neutron",
            "hydrogen", "helium", "carbon", "nitrogen", "oxygen", "sodium",
            "chlorine", "sulfur", "potassium", "calcium", "iron", "copper",
        ],
        "quick_command": "nguyên tử khối của Fe là bao nhiêu?",
    },
    "molar_mass": {
        "description": "Tính khối lượng mol cho công thức hóa học.",
        "keywords": [
            "khối lượng mol", "molar mass", "công thức hóa học",
            "mol", "phân tử khối", "tính mol", "H2O", "NaCl",
        ],
        "quick_command": "khối lượng mol của H2O",
    },
    "wiki_search": {
        "description": "Tìm kiếm và tra cứu thông tin về nhân vật, sự kiện lịch sử, khái niệm khoa học, địa danh, tổ chức qua Wikipedia.",
        "keywords": [
            "là ai", "là gì", "là người", "là nhà", "là tổ chức",
            "nhân vật", "người nổi tiếng", "nhà khoa học", "nhà phát minh",
            "lịch sử", "sự kiện", "chiến tranh", "cách mạng",
            "khoa học", "phát minh", "khám phá", "lý thuyết",
            "địa danh", "quốc gia", "thành phố", "châu lục",
            "wikipedia", "wiki", "tìm kiếm",
            "cho tôi biết về", "giới thiệu về", "thông tin về",
        ],
        "quick_command": "Albert Einstein là ai?",
    },
}


def apply(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    for name, data in UPDATES.items():
        tools = MCPTool.objects.filter(name__iendswith=name)
        count = tools.update(
            keywords=data["keywords"],
            description=data["description"],
            quick_command=data.get("quick_command", ""),
        )
        print(f"  {'Updated' if count else 'Not found'} {count}x: {name}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0034_update_tool_keywords'),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]

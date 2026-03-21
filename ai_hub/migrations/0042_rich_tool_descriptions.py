"""
Migration 0042: Cập nhật description chi tiết + quick_command cho tất cả tools.
Router giờ dùng pure semantic — description phải đủ phong phú để phân biệt tools.
"""
from django.db import migrations

# Mỗi tool có:
#   description: mô tả dài, chi tiết, bao gồm các trường hợp sử dụng
#   quick_command: ví dụ câu hỏi thực tế người dùng hay hỏi (dùng để embed)
TOOL_UPDATES = {
    "japanese_lookup": {
        "description": (
            "Tra cứu từ tiếng Nhật qua Jisho.org. Dùng khi người dùng hỏi về nghĩa, cách đọc, "
            "cách viết của một từ tiếng Nhật — bao gồm Kanji, Hiragana, Katakana, Romaji. "
            "Ví dụ: kimochi nghĩa là gì, kawaii tiếng Nhật là gì, từ sakura trong tiếng Nhật, "
            "arigatou có nghĩa là gì, suki tiếng Nhật nghĩa là gì, "
            "tra từ tiếng Nhật, từ điển Nhật, nghĩa tiếng Nhật của từ nào đó, "
            "chữ Nhật, kanji của từ nào, cách đọc tiếng Nhật."
        ),
        "quick_command": "kimochi tiếng Nhật nghĩa là gì?",
    },
    "english_define": {
        "description": (
            "Tra nghĩa từ tiếng Anh qua Free Dictionary API. Dùng khi người dùng hỏi về nghĩa, "
            "định nghĩa, cách dùng của một từ tiếng Anh. "
            "Ví dụ: requiem tiếng Anh nghĩa là gì, define serendipity, "
            "từ ephemeral có nghĩa là gì, nghĩa của từ resilience, "
            "tra từ điển tiếng Anh, từ này tiếng Anh là gì, "
            "what does melancholy mean, definition of ubiquitous."
        ),
        "quick_command": "requiem tiếng Anh nghĩa là gì?",
    },
    "wiki_search": {
        "description": (
            "Tìm kiếm thông tin bách khoa trên Wikipedia. Dùng khi người dùng hỏi về "
            "nhân vật lịch sử, nhà khoa học, chính trị gia, nghệ sĩ, vận động viên, "
            "sự kiện lịch sử, chiến tranh, cách mạng, phát minh, khám phá khoa học, "
            "địa danh, quốc gia, thành phố, tổ chức, công ty, khái niệm học thuật. "
            "Ví dụ: Albert Einstein là ai, Hồ Chí Minh là ai, "
            "lịch sử chiến tranh Việt Nam, thành phố Paris ở đâu, "
            "thuyết tương đối là gì, DNA là gì, cách mạng công nghiệp là gì, "
            "giới thiệu về Newton, tiểu sử Marie Curie."
        ),
        "quick_command": "Albert Einstein là ai?",
    },
    "wiki_summary": {
        "description": (
            "Lấy tóm tắt bài viết Wikipedia theo tiêu đề cụ thể. Dùng khi người dùng "
            "muốn tóm tắt nội dung một bài Wikipedia cụ thể theo tên bài. "
            "Ví dụ: tóm tắt bài về Thế chiến II, tóm tắt Wikipedia về Python programming."
        ),
        "quick_command": "tóm tắt bài Wikipedia về Thế chiến II",
    },
    "calc": {
        "description": (
            "Tính toán biểu thức toán học. Dùng khi người dùng muốn tính một phép tính, "
            "biểu thức số học, hàm toán học. "
            "Ví dụ: tính sqrt(144) + 5^2, tính 2^10, tính sin(30), "
            "tính (100 * 3.14) / 2, kết quả của 15! là bao nhiêu, "
            "tính log(1000), tính 3/4 + 1/2, bao nhiêu là 25% của 200."
        ),
        "quick_command": "tính sqrt(144) + 5^2",
    },
    "balance_equation": {
        "description": (
            "Cân bằng phương trình hóa học. Dùng khi người dùng muốn cân bằng một phản ứng hóa học, "
            "tìm hệ số cân bằng cho các chất trong phương trình. "
            "Ví dụ: cân bằng H2 + O2 = H2O, cân bằng Fe + O2 = Fe2O3, "
            "cân bằng phương trình CH4 + O2 = CO2 + H2O, "
            "cân bằng phản ứng hóa học, hệ số cân bằng của phương trình."
        ),
        "quick_command": "cân bằng phương trình H2 + O2 = H2O",
    },
    "molar_mass": {
        "description": (
            "Tính khối lượng mol của hợp chất hóa học. Dùng khi người dùng muốn biết "
            "khối lượng mol (g/mol) của một công thức hóa học. "
            "Ví dụ: khối lượng mol của H2O, tính mol của NaCl, "
            "khối lượng mol H2SO4, tính M của CaCO3, "
            "phân tử khối của glucose C6H12O6."
        ),
        "quick_command": "khối lượng mol của H2O là bao nhiêu?",
    },
    "lookup_element": {
        "description": (
            "Tra cứu thông tin nguyên tố hóa học trong bảng tuần hoàn. Dùng khi người dùng "
            "hỏi về số hiệu nguyên tử, nguyên tử khối, ký hiệu hóa học của một nguyên tố. "
            "Ví dụ: nguyên tố nhôm trong bảng tuần hoàn, số hiệu nguyên tử của sắt, "
            "ký hiệu hóa học của vàng, nguyên tử khối của carbon, "
            "thông tin về nguyên tố oxy, tra cứu nguyên tố Na."
        ),
        "quick_command": "nguyên tố nhôm trong bảng tuần hoàn",
    },
    "physics_solve": {
        "description": (
            "Giải bài toán vật lý cơ bản. Dùng khi người dùng hỏi về các công thức vật lý, "
            "tính toán liên quan đến động học, điện học, nhiệt học, quang học. "
            "Ví dụ: tính vận tốc khi biết gia tốc và thời gian, "
            "tính điện trở theo định luật Ohm, tính công suất điện, "
            "bài toán vật lý về chuyển động, tính lực ma sát."
        ),
        "quick_command": "tính vận tốc khi gia tốc 5 m/s² trong 10 giây",
    },
    "chemistry_lookup": {
        "description": (
            "Tra cứu thông tin hóa học tổng quát: nguyên tố, phản ứng, hợp chất. "
            "Dùng khi người dùng hỏi về tính chất hóa học, ứng dụng của nguyên tố hoặc hợp chất. "
            "Ví dụ: tính chất của nhôm, ứng dụng của sắt trong công nghiệp, "
            "phản ứng của axit với bazơ, hóa học của nước, "
            "tính chất của NaOH, ứng dụng của CO2."
        ),
        "quick_command": "tính chất hóa học của nhôm",
    },
    "ohms_law": {
        "description": (
            "Tính toán theo định luật Ohm (U = I × R). Dùng khi người dùng muốn tính "
            "điện áp, cường độ dòng điện, hoặc điện trở trong mạch điện. "
            "Ví dụ: tính điện áp khi I=2A và R=5Ω, tính dòng điện khi U=12V R=4Ω, "
            "định luật Ohm, tính điện trở mạch điện."
        ),
        "quick_command": "tính điện áp khi dòng điện 2A và điện trở 5 ohm",
    },
    "kinematics_v": {
        "description": (
            "Tính vận tốc theo công thức động học v = v0 + at. Dùng khi người dùng "
            "muốn tính vận tốc cuối, vận tốc đầu, gia tốc hoặc thời gian trong chuyển động thẳng. "
            "Ví dụ: tính vận tốc sau 5 giây với gia tốc 3 m/s², "
            "vật chuyển động với v0=0 a=9.8 t=2."
        ),
        "quick_command": "tính vận tốc sau 5 giây với gia tốc 3 m/s²",
    },
    "quadratic": {
        "description": (
            "Giải phương trình bậc 2 (ax² + bx + c = 0). Dùng khi người dùng muốn "
            "tìm nghiệm của phương trình bậc hai. "
            "Ví dụ: giải x² - 5x + 6 = 0, nghiệm của 2x² + 3x - 2 = 0, "
            "phương trình bậc 2, tìm x trong phương trình bậc hai."
        ),
        "quick_command": "giải phương trình x² - 5x + 6 = 0",
    },
    "stats_basic": {
        "description": (
            "Tính thống kê cơ bản: trung bình, trung vị, độ lệch chuẩn, min, max. "
            "Dùng khi người dùng có một dãy số và muốn tính các chỉ số thống kê. "
            "Ví dụ: tính trung bình của 5 7 3 9 2, độ lệch chuẩn của dãy số, "
            "thống kê mô tả, tính mean median của dữ liệu."
        ),
        "quick_command": "tính trung bình và độ lệch chuẩn của 5 7 3 9 2",
    },
    "constants": {
        "description": (
            "Tra cứu hằng số vật lý và hóa học. Dùng khi người dùng hỏi về giá trị "
            "của các hằng số khoa học như tốc độ ánh sáng, hằng số Planck, số Avogadro. "
            "Ví dụ: tốc độ ánh sáng là bao nhiêu, hằng số Planck, số Avogadro, "
            "hằng số khí lý tưởng R, gia tốc trọng trường g."
        ),
        "quick_command": "tốc độ ánh sáng là bao nhiêu?",
    },
    "time_now": {
        "description": (
            "Lấy thời gian hiện tại. Dùng khi người dùng hỏi về giờ, ngày, tháng, năm hiện tại. "
            "Ví dụ: bây giờ là mấy giờ, hôm nay là ngày mấy, ngày hôm nay là gì, "
            "thời gian hiện tại, what time is it now."
        ),
        "quick_command": "bây giờ là mấy giờ?",
    },
    "system_info": {
        "description": (
            "Lấy thông tin hệ thống máy chủ. Dùng khi người dùng hỏi về trạng thái server, "
            "CPU, RAM, hệ điều hành của hệ thống DTHub. "
            "Ví dụ: thông tin hệ thống, server đang chạy gì, CPU usage, RAM còn bao nhiêu."
        ),
        "quick_command": "thông tin hệ thống server hiện tại",
    },
    "rag_search": {
        "description": (
            "Tìm kiếm thông tin trong tài liệu đã upload của người dùng (PDF, DOCX, TXT). "
            "Dùng khi người dùng hỏi về nội dung tài liệu, luận văn, báo cáo, file đã tải lên. "
            "Ví dụ: tài liệu nói gì về chương 3, tóm tắt luận văn của tôi, "
            "nội dung chính của báo cáo, file tôi upload có đề cập đến gì."
        ),
        "quick_command": "tài liệu tôi upload nói về chủ đề gì?",
    },
}


def apply(apps, schema_editor):
    MCPTool = apps.get_model("ai_hub", "MCPTool")
    for name, data in TOOL_UPDATES.items():
        # Match cả tên trực tiếp lẫn tên có prefix local-mcp-XXXX_
        qs = MCPTool.objects.filter(name=name) | MCPTool.objects.filter(name__endswith=f"_{name}")
        updated = qs.update(
            description=data["description"],
            quick_command=data.get("quick_command", ""),
        )
        if updated:
            print(f"  Updated {updated}x: {name}")
        else:
            print(f"  NOT FOUND: {name}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("ai_hub", "0041_fix_wiki_search_keywords"),
    ]

    operations = [
        migrations.RunPython(apply, noop),
    ]

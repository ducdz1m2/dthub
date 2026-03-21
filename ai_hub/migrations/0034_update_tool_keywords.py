"""
Migration: cập nhật keywords cho tất cả MCPTool để router nhận diện tốt hơn.
"""
from django.db import migrations


TOOL_KEYWORDS = {
    "wiki_search": {
        "description": "Tìm kiếm và tra cứu thông tin về nhân vật, sự kiện lịch sử, khái niệm khoa học, địa danh, tổ chức qua Wikipedia.",
        "keywords": [
            "là ai", "là gì", "là người", "là nhà", "là tổ chức",
            "nhân vật", "người nổi tiếng", "nhà khoa học", "nhà phát minh",
            "lịch sử", "sự kiện", "chiến tranh", "cách mạng",
            "khoa học", "phát minh", "khám phá", "lý thuyết",
            "địa danh", "quốc gia", "thành phố", "châu lục",
            "wikipedia", "wiki", "tìm kiếm", "tra cứu",
            "cho tôi biết về", "giới thiệu về", "thông tin về",
        ],
        "quick_command": "Albert Einstein là ai?",
    },
    "wiki_summary": {
        "description": "Lấy tóm tắt chi tiết về một chủ đề, nhân vật, sự kiện từ Wikipedia.",
        "keywords": [
            "tóm tắt", "tóm lược", "mô tả", "giới thiệu",
            "wiki summary", "wikipedia", "nội dung về", "thông tin về",
        ],
        "quick_command": "tóm tắt về Python lập trình",
    },
    "rag_search": {
        "description": "Tra cứu tài liệu, luận văn, báo cáo đã được tải lên bởi người dùng.",
        "keywords": [
            "tài liệu", "luận văn", "báo cáo", "file đã upload", "đã tải lên",
            "trong tài liệu", "tìm trong", "nội dung file", "nội dung tài liệu",
            "tra cứu", "quyển", "cuốn", "bclv", "khóa luận", "đề tài",
            "nói về chủ đề", "chủ đề gì", "viết về", "nghiên cứu về",
            "tóm tắt tài liệu", "nội dung chính", "kết luận của",
        ],
        "quick_command": "luận văn BCLV_B1706860 nói về đề tài gì?",
    },
    "english_define": {
        "description": "Tra nghĩa từ tiếng Anh, từ điển Anh-Việt.",
        "keywords": [
            "nghĩa của", "tra từ", "từ điển", "tiếng anh", "english",
            "define", "definition", "nghĩa là gì", "từ này nghĩa",
        ],
        "quick_command": "từ 'resilient' nghĩa là gì?",
    },
    "translate": {
        "description": "Dịch văn bản giữa các ngôn ngữ.",
        "keywords": [
            "dịch", "translate", "dịch sang", "dịch tiếng", "chuyển ngữ",
            "dịch ra", "dịch từ", "dịch câu",
        ],
        "quick_command": "dịch 'hello world' sang tiếng Việt",
    },
    "japanese_lookup": {
        "description": "Tra cứu từ/kanji tiếng Nhật qua Jisho.org.",
        "keywords": [
            "tiếng nhật", "japanese", "kanji", "hiragana", "katakana",
            "jisho", "tra từ nhật", "nhật bản", "chữ nhật",
        ],
        "quick_command": "勉強 nghĩa là gì?",
    },
    "calc": {
        "description": "Tính biểu thức toán học (cộng, trừ, nhân, chia, lũy thừa, sqrt, sin, cos, log...).",
        "keywords": [
            "tính", "tính toán", "calc", "biểu thức", "bằng bao nhiêu",
            "kết quả", "sqrt", "sin", "cos", "log", "cộng", "trừ", "nhân", "chia",
        ],
        "quick_command": "tính sqrt(144) + 5^2",
    },
    "quadratic": {
        "description": "Giải phương trình bậc 2: ax²+bx+c=0.",
        "keywords": [
            "phương trình bậc 2", "quadratic", "ax2", "ax²",
            "giải phương trình", "delta", "nghiệm",
        ],
        "quick_command": "giải phương trình x² - 5x + 6 = 0",
    },
    "stats_basic": {
        "description": "Thống kê cơ bản (min/max/mean/median) cho danh sách số.",
        "keywords": [
            "thống kê", "trung bình", "median", "min", "max", "mean",
            "stats", "trung vị", "giá trị lớn nhất", "giá trị nhỏ nhất",
        ],
        "quick_command": "tính trung bình của [1, 2, 3, 4, 5]",
    },
    "ohms_law": {
        "description": "Tính V/I/R theo định luật Ohm (V=I*R).",
        "keywords": [
            "ohm", "định luật ohm", "điện trở", "điện áp",
            "cường độ dòng điện", "v=ir", "vật lý điện",
        ],
        "quick_command": "tính V với I=2A, R=10Ω",
    },
    "kinematics_v": {
        "description": "Tính vận tốc theo công thức động học v = u + a*t.",
        "keywords": [
            "động học", "kinematics", "vận tốc", "gia tốc",
            "v=u+at", "chuyển động", "vật lý cơ học",
        ],
        "quick_command": "tính v với u=0, a=9.8, t=3",
    },
    "constants": {
        "description": "Trả về hằng số vật lý cơ bản (g, c, R).",
        "keywords": [
            "hằng số", "constants", "gia tốc trọng trường",
            "tốc độ ánh sáng", "hằng số khí",
        ],
        "quick_command": "hằng số vật lý g là bao nhiêu?",
    },
    "lookup_element": {
        "description": "Tra cứu nguyên tố hóa học theo ký hiệu (H, O, Na...) hoặc tên.",
        "keywords": [
            "nguyên tố", "tra cứu nguyên tố", "element", "ký hiệu hóa học",
            "hóa học", "hydro", "oxi", "natri", "sắt", "canxi",
            "hydrogen", "oxygen", "sodium", "iron", "calcium",
        ],
        "quick_command": "tra cứu nguyên tố Fe",
    },
    "molar_mass": {
        "description": "Tính khối lượng mol cho công thức hóa học.",
        "keywords": [
            "khối lượng mol", "molar mass", "công thức hóa học",
            "mol", "phân tử", "H2O", "NaCl",
        ],
        "quick_command": "khối lượng mol của H2O",
    },
    "balance_equation": {
        "description": "Cân bằng phương trình hóa học.",
        "keywords": [
            "cân bằng phương trình", "phương trình hóa học",
            "balance equation", "hóa học",
        ],
        "quick_command": "cân bằng H2 + O2 = H2O",
    },
    "device_control": {
        "description": "Điều khiển thiết bị IoT (bật/tắt quạt, đèn, relay...).",
        "keywords": [
            "bật", "tắt", "điều khiển", "thiết bị", "relay",
            "quạt", "đèn", "iot", "device", "mở", "đóng",
        ],
        "quick_command": "bật đèn phòng khách",
    },
    "list_devices": {
        "description": "Liệt kê danh sách thiết bị IoT đang online/offline.",
        "keywords": [
            "danh sách thiết bị", "thiết bị nào", "online", "offline",
            "list devices", "thiết bị đang kết nối",
        ],
        "quick_command": "liệt kê thiết bị đang online",
    },
    "get_user_info": {
        "description": "Lấy thông tin tài khoản của người dùng hiện tại.",
        "keywords": [
            "thông tin tài khoản", "thông tin của tôi", "tôi là ai", "tên tôi",
            "email của tôi", "số điện thoại", "profile", "tài khoản", "hồ sơ",
            "bạn biết gì về tôi",
        ],
        "quick_command": "thông tin tài khoản của tôi",
    },
    "list_products": {
        "description": "Liệt kê sản phẩm có trên sàn (tên, giá, loại, tồn kho).",
        "keywords": [
            "sản phẩm", "danh sách sản phẩm", "có bán gì", "mua gì",
            "giá", "tồn kho", "shop", "cửa hàng", "product",
        ],
        "quick_command": "có bán những sản phẩm gì?",
    },
    "get_order_status": {
        "description": "Xem trạng thái đơn hàng của người dùng.",
        "keywords": [
            "đơn hàng", "trạng thái đơn", "đơn của tôi", "order",
            "đặt hàng", "lắp đặt", "thi công", "nghiệm thu",
        ],
        "quick_command": "trạng thái đơn hàng của tôi",
    },
    "time_now": {
        "description": "Lấy thời gian hiện tại theo timezone.",
        "keywords": [
            "thời gian", "giờ hiện tại", "mấy giờ", "ngày hôm nay",
            "time", "timezone", "Asia/Ho_Chi_Minh",
        ],
        "quick_command": "bây giờ là mấy giờ?",
    },
    "system_info": {
        "description": "Thông tin hệ thống (thời gian, CPU, RAM).",
        "keywords": [
            "hệ thống", "system", "cpu", "ram", "thời gian",
            "thông tin máy", "server info",
        ],
        "quick_command": "thông tin hệ thống",
    },
    "weather_info": {
        "description": "Thông tin thời tiết theo thành phố.",
        "keywords": [
            "thời tiết", "weather", "nhiệt độ", "hanoi", "hcm",
            "mưa", "nắng", "dự báo thời tiết",
        ],
        "quick_command": "thời tiết Hà Nội hôm nay",
    },
}


def update_keywords(apps, schema_editor):
    MCPTool = apps.get_model('ai_hub', 'MCPTool')
    for name, data in TOOL_KEYWORDS.items():
        # Match both bare name and prefixed names (e.g. local-mcp-8001_rag_search)
        tools = MCPTool.objects.filter(name__iendswith=name)
        count = tools.update(
            keywords=data["keywords"],
            description=data["description"],
            quick_command=data.get("quick_command", ""),
        )
        if count:
            print(f"  Updated {count}x: {name}")
        else:
            print(f"  Not found (skip): {name}")


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ai_hub', '0033_userdocument_add_file_field'),
    ]

    operations = [
        migrations.RunPython(update_keywords, noop),
    ]

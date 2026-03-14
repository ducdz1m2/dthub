"""
System Tools - Các công cụ hệ thống (thời gian, thời tiết, trợ giúp)
"""

import datetime
import platform


def register_system_tools(dispatcher):
    """Đăng ký các tool hệ thống vào dispatcher"""
    
    def mcp_system_info(query):
        """Lấy thông tin hệ thống: thời gian, ngày tháng, trạng thái server"""
        try:
            import time
            import psutil
            from django.utils import timezone
            from django.conf import settings
            import django
            
            query_lower = query.lower()
            
            # Thông tin thời gian - sửa để hiển thị đúng local time và UTC
            now_utc = datetime.datetime.utcnow()
            now_local = datetime.datetime.now()
            
            # Format thời gian
            time_info = f"Thời gian hệ thống:\n"
            time_info += f"- Giờ địa phương: {now_local.strftime('%H:%M:%S %d/%m/%Y')}\n"
            time_info += f"- UTC: {now_utc.strftime('%H:%M:%S %d/%m/%Y')}\n"
            time_info += f"- Múi giờ: UTC+7 (Asia/Ho_Chi_Minh)\n"
            
            # Thông tin hệ thống
            system_info = f"\nThông tin hệ thống:\n"
            system_info += f"- Hệ điều hành: {platform.system()} {platform.release()}\n"
            system_info += f"- Python: {platform.python_version()}\n"
            
            # CPU và Memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            system_info += f"- CPU: {cpu_percent}%\n"
            system_info += f"- RAM: {memory.percent}% ({memory.used//1024//1024}MB/{memory.total//1024//1024}MB)\n"
            
            # Thông tin Django
            django_info = f"\nThông tin Django:\n"
            django_info += f"- Debug mode: {'Bật' if settings.DEBUG else 'Tắt'}\n"
            django_info += f"- Phiên bản Django: {django.get_version() if hasattr(django, 'get_version') else 'N/A'}\n"
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                django_info += f"- Database: Kết nối thành công\n"
            except:
                django_info += f"- Database: Mất kết nối\n"
            
            # Tùy chọn theo query
            if 'thời gian' in query_lower or 'time' in query_lower or 'giờ' in query_lower:
                return time_info
            elif 'hệ thống' in query_lower or 'system' in query_lower or 'cpu' in query_lower or 'ram' in query_lower:
                return system_info
            elif 'django' in query_lower:
                return django_info
            else:
                return time_info + system_info + django_info
                
        except Exception as e:
            return f"Lỗi khi lấy thông tin hệ thống: {str(e)}"
    
    def mcp_weather_info(query):
        """Lấy thông tin thời tiết (mock hoặc API)"""
        try:
            query_lower = query.lower()
            
            # Mock weather data - mở rộng thêm nhiều thành phố Việt Nam
            weather_data = {
                # Miền Bắc
                "hanoi": {"temp": 28, "humidity": 75, "condition": "Có mây", "wind": "5 km/h", "region": "Miền Bắc"},
                "ha noi": {"temp": 28, "humidity": 75, "condition": "Có mây", "wind": "5 km/h", "region": "Miền Bắc"},
                "hải phòng": {"temp": 27, "humidity": 78, "condition": "Có mây", "wind": "6 km/h", "region": "Miền Bắc"},
                "hai phong": {"temp": 27, "humidity": 78, "condition": "Có mây", "wind": "6 km/h", "region": "Miền Bắc"},
                # Miền Trung
                "danang": {"temp": 29, "humidity": 70, "condition": "Nắng nhẹ", "wind": "6 km/h", "region": "Miền Trung"},
                "da nang": {"temp": 29, "humidity": 70, "condition": "Nắng nhẹ", "wind": "6 km/h", "region": "Miền Trung"},
                "huế": {"temp": 28, "humidity": 72, "condition": "Nhiều mây", "wind": "4 km/h", "region": "Miền Trung"},
                "nha trang": {"temp": 30, "humidity": 68, "condition": "Nắng", "wind": "7 km/h", "region": "Miền Trung"},
                # Miền Nam
                "hcm": {"temp": 30, "humidity": 80, "condition": "Nắng", "wind": "8 km/h", "region": "Miền Nam"},
                "ho chi minh": {"temp": 30, "humidity": 80, "condition": "Nắng", "wind": "8 km/h", "region": "Miền Nam"},
                "hồ chí minh": {"temp": 30, "humidity": 80, "condition": "Nắng", "wind": "8 km/h", "region": "Miền Nam"},
                "cần thơ": {"temp": 31, "humidity": 82, "condition": "Nắng", "wind": "5 km/h", "region": "Miền Nam"},
                "can tho": {"temp": 31, "humidity": 82, "condition": "Nắng", "wind": "5 km/h", "region": "Miền Nam"},
                "vũng tàu": {"temp": 29, "humidity": 77, "condition": "Nắng nhẹ", "wind": "6 km/h", "region": "Miền Nam"},
                "vung tau": {"temp": 29, "humidity": 77, "condition": "Nắng nhẹ", "wind": "6 km/h", "region": "Miền Nam"},
            }
            
            # Mapping tên thành phố
            city_mappings = {
                "thủ đô": "hanoi", "thu do": "hanoi", "hà nội": "hanoi",
                "sài gòn": "hcm", "sai gon": "hcm", "tp hcm": "hcm", "tp.hcm": "hcm",
                "đà nẵng": "danang",
                "cần thơ": "can tho", "cantho": "can tho",
            }
            
            # Tìm thành phố trong query
            city = None
            # Kiểm tra mapping trước
            for name, mapped in city_mappings.items():
                if name in query_lower:
                    city = mapped
                    break
            
            # Nếu không có mapping, tìm trực tiếp
            if not city:
                for city_name in weather_data.keys():
                    if city_name in query_lower:
                        city = city_name
                        break
            
            if not city:
                # Trích xuất tên thành phố từ query
                for prefix in ["thời tiết", "thoi tiet", "weather", "tại", "tai", "ở", "o"]:
                    if query_lower.startswith(prefix):
                        query_lower = query_lower[len(prefix):].strip()
                # Nếu query còn lại có thể là tên thành phố
                if query_lower and len(query_lower) > 2:
                    city = query_lower
                else:
                    city = "hanoi"  # Mặc định
            
            data = weather_data.get(city)
            if not data:
                # Thành phố không có trong dữ liệu - trả về dữ liệu mẫu generic
                return f"Xin lỗi, hiện tại tôi chưa có dữ liệu thời tiết cho '{city.title()}'.\n\nTôi chỉ có dữ liệu cho các thành phố: Hà Nội, Đà Nẵng, TP.HCM, Hải Phòng, Huế, Nha Trang, Cần Thơ, Vũng Tàu.\n\nDữ liệu mẫu cho Hà Nội:\n- Nhiệt độ: 28°C\n- Độ ẩm: 75%\n- Tình trạng: Có mây\n- Gió: 5 km/h"
            
            response = f"Thời tiết {city.title()} ({data['region']}):\n"
            response += f"- Nhiệt độ: {data['temp']}°C\n"
            response += f"- Độ ẩm: {data['humidity']}%\n"
            response += f"- Tình trạng: {data['condition']}\n"
            response += f"- Gió: {data['wind']}\n"
            response += f"\n*Đây là dữ liệu tham khảo - có thể tích hợp API thời tiết thực tế*"
            
            return response
            
        except Exception as e:
            return f"Lỗi khi lấy thông tin thời tiết: {str(e)}"
    
    def mcp_help_info(query):
        """Hiển thị trợ giúp về các lệnh có sẵn"""
        try:
            help_text = "Tro giup DTHub - Cac lenh co san:\n\n"
            
            help_text += "**Dieu khien thiet bi IoT:**\n"
            help_text += "- 'bật quạt', 'tắt đèn', 'mở cửa', 'đóng relay'\n"
            help_text += "- 'liệt kê thiết bị', 'xem thiết bị'\n\n"
            
            help_text += "**Doc cam bien:**\n"
            help_text += "- 'đọc nhiệt độ', 'đọc độ ẩm', 'sensor read'\n"
            help_text += "- 'kiểm tra cảm biến', 'dữ liệu cảm biến'\n\n"
            
            help_text += "**Tra cuu thong tin:**\n"
            help_text += "- 'tìm kiếm [từ khóa]', 'wikipedia [chủ đề]'\n"
            help_text += "- 'tóm tắt [chủ đề]', 'tra cứu [thông tin]'\n\n"
            
            help_text += "**Tu dien:**\n"
            help_text += "- 'tiếng anh là [từ]', 'define [word]'\n"
            help_text += "- 'tiếng nhật [từ]', 'kanji [ký tự]'\n\n"
            
            help_text += "**Tinh toan:**\n"
            help_text += "- 'tính V theo định luật Ohm', 'vật lý [bài toán]'\n"
            help_text += "- 'khối lượng mol của H2O', 'hóa học [công thức]'\n\n"
            
            help_text += "**Thong tin he thong:**\n"
            help_text += "- 'thời gian hệ thống', 'thông tin hệ thống'\n"
            help_text += "- 'thời tiết hanoi', 'weather hcm'\n\n"
            
            help_text += "**Tro chuyen:**\n"
            help_text += "- 'chào', 'xin chào', 'cảm ơn', 'tạm biệt'"
            
            return help_text
            
        except Exception as e:
            return f"Lỗi khi hiển thị trợ giúp: {str(e)}"

    def mcp_tool_metadata(query):
        """Trả lời về nguồn gốc và cách thức hoạt động của các công cụ"""
        import re
        query_lower = query.lower()
        
        # Danh sách metadata cho các tool
        tool_info = {
            "weather": {
                "keywords": ["thời tiết", "weather", "nhiệt độ", "độ ẩm", "mưa", "nắng"],
                "name": "Thông tin thời tiết",
                "source": "Dữ liệu mock được hard-code trong hệ thống (chưa kết nối API thời tiết thực tế)",
                "cities": ["Hà Nội", "Hải Phòng", "Đà Nẵng", "Huế", "Nha Trang", "TP.HCM", "Cần Thơ", "Vũng Tàu"],
                "how_it_works": "Tìm kiếm tên thành phố trong query, tra khớp với dictionary dữ liệu mẫu và trả về nhiệt độ, độ ẩm, tình trạng thời tiết."
            },
            "wikipedia": {
                "keywords": ["wikipedia", "wiki", "tìm kiếm", "tóm tắt"],
                "name": "Tìm kiếm Wikipedia",
                "source": "API Wikipedia (wikipedia.org) qua module builtins",
                "how_it_works": "Gọi API Wikipedia để tìm kiếm/tóm tắt thông tin từ Wikipedia tiếng Việt."
            },
            "dictionary": {
                "keywords": ["từ điển", "dictionary", "tiếng anh", "tiếng nhật", "nghĩa là", "define"],
                "name": "Tra cứu từ điển",
                "source": "Free Dictionary API (tiếng Anh) và Jisho API (tiếng Nhật)",
                "how_it_works": "Trích xuất từ khóa từ query, gọi API tương ứng để lấy định nghĩa, phiên âm, ví dụ."
            },
            "device_control": {
                "keywords": ["bật", "tắt", "mở", "đóng", "thiết bị", "quạt", "đèn", "relay"],
                "name": "Điều khiển thiết bị IoT",
                "source": "ESP32/ESP8266 devices trong database nội bộ",
                "how_it_works": "Tìm nhãn thiết bị trong database, gửi HTTP request đến IP của thiết bị để bật/tắt."
            },
            "rag": {
                "keywords": ["rag", "tìm kiếm", "database", "tài liệu", "thông tin nội bộ"],
                "name": "RAG Search (Retrieval-Augmented Generation)",
                "source": "Vector database FAISS chứa tài liệu nội bộ (Đại học Cần Thơ, thương hiệu, v.v.)",
                "how_it_works": "Dùng vector search để tìm tài liệu liên quan trong FAISS index, kết hợp với LLM để trả lời."
            },
            "physics": {
                "keywords": ["vật lý", "physics", "định luật ohm", "tính toán"],
                "name": "Tính toán Vật lý",
                "source": "Các công thức vật lý được hard-code trong builtins module",
                "how_it_works": "Trích xuất tham số từ query, áp dụng công thức vật lý tương ứng."
            },
            "chemistry": {
                "keywords": ["hóa học", "chemistry", "khối lượng mol", "nguyên tố"],
                "name": "Tính toán Hóa học",
                "source": "Periodic table data và công thức hóa học trong builtins module",
                "how_it_works": "Phân tích công thức hóa học, tra bảng tuần hoàn, tính khối lượng mol."
            },
            "system": {
                "keywords": ["hệ thống", "system", "cpu", "ram", "thời gian"],
                "name": "Thông tin hệ thống",
                "source": "Trực tiếp từ server (psutil, platform, Django)",
                "how_it_works": "Đọc thông tin phần cứng, thời gian, trạng thái server hiện tại."
            },
            "llm": {
                "keywords": ["llm", "ai", "ollama", "model", "trí tuệ nhân tạo"],
                "name": "Language Model (LLM)",
                "source": "Ollama local server (Llama 3, Mistral, v.v.)",
                "how_it_works": "Gửi prompt (query + context từ tool) đến Ollama API, nhận streaming response."
            }
        }
        
        # Xác định tool nào được hỏi
        matched_tool = None
        for tool_key, info in tool_info.items():
            for kw in info["keywords"]:
                if kw in query_lower:
                    matched_tool = tool_key
                    break
            if matched_tool:
                break
        
        # Nếu không match cụ thể, trả lời chung
        if not matched_tool:
            response = "Hệ thống DTHub AI sử dụng nhiều nguồn dữ liệu khác nhau:\n\n"
            for key, info in tool_info.items():
                response += f"**{info['name']}**: {info['source']}\n"
            response += "\nHỏi cụ thể về từng chức năng để biết chi tiết hơn (VD: 'thông tin thời tiết lấy từ đâu?')"
            return response
        
        # Trả lời chi tiết về tool được hỏi
        info = tool_info[matched_tool]
        response = f"**{info['name']}**\n\n"
        response += f"📍 **Nguồn dữ liệu**: {info['source']}\n\n"
        response += f"⚙️ **Cách hoạt động**: {info['how_it_works']}\n"
        
        if "cities" in info:
            response += f"\n🏙️ **Các thành phố hỗ trợ**: {', '.join(info['cities'])}"
        
        return response

    # Đăng ký tools
    dispatcher.tools["system_info"] = {
        "handler": mcp_system_info,
        "description": "Lấy thông tin hệ thống: thời gian, ngày tháng, trạng thái server, CPU, RAM.",
        "keywords": ["thời gian", "hệ thống", "system", "thông tin", "server", "cpu", "ram", "datetime", "time"]
    }
    
    dispatcher.tools["weather_info"] = {
        "handler": mcp_weather_info,
        "description": "Lấy thông tin thời tiết của các thành phố (Hà Nội, HCM, Đà Nẵng).",
        "keywords": ["thời tiết", "weather", "nhiệt độ", "hanoi", "hcm", "đà nẵng", "danang", "mưa", "nắng"]
    }
    
    dispatcher.tools["help_info"] = {
        "handler": mcp_help_info,
        "description": "Hiển thị trợ giúp và danh sách các lệnh có sẵn của trợ lý DTHub.",
        "keywords": ["trợ giúp", "help", "hướng dẫn", "lệnh", "commands", "danh sách", "tôi có thể làm gì"]
    }
    
    dispatcher.tools["tool_metadata"] = {
        "handler": mcp_tool_metadata,
        "description": "Trả lời về nguồn gốc, cách thức hoạt động của các công cụ AI và dữ liệu.",
        "keywords": ["lấy ở đâu", "từ đâu ra", "nguồn", "source", "cách hoạt động", "cơ chế", "dữ liệu từ đâu", "thông tin này ở đâu", "ai lấy từ đâu", "lấy thông tin ở đâu", "dữ liệu ở đâu"],
        "priority": 100  # Highest priority to override other tools when asking about sources
    }
    
    print("System tools registered successfully")

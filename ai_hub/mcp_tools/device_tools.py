"""
Device Tools - Các công cụ điều khiển thiết bị IoT và liệt kê thiết bị
"""

import requests


def register_device_tools(dispatcher):
    """Đăng ký các tool điều khiển thiết bị vào dispatcher"""
    
    def mcp_device_control(query):
        try:
            from ..models import DeviceControlLabel, ESP32Device
            query_lower = query.lower()
            print(f"DEBUG: Nhan lenh dieu khien: '{query}'")
            
            # 1. TÌM KIẾM NHÃN THIẾT BỊ TỪ DATABASE (Sắp xếp theo độ dài nhãn giảm dần để tránh trùng lặp)
            all_labels = DeviceControlLabel.objects.filter(is_active=True).select_related('device').order_by('-label')
            
            target_label = None
            for label_obj in all_labels:
                label_name = label_obj.label.lower()
                if label_name in query_lower:
                    target_label = label_obj
                    print(f"DEBUG: Tim thay nhan '{label_name}' khop voi yeu cau")
                    break
            
            if not target_label:
                available_labels = ", ".join([l.label for l in all_labels])
                print(f"DEBUG: Khong tim thay nhan nao khop. Cac nhan hien co: {available_labels}")
                return f"Tôi không tìm thấy thiết bị nào có nhãn tương ứng. Hiện tại hệ thống đang có các nhãn: {available_labels if available_labels else 'Chưa có nhãn nào'}. Hãy thử gán nhãn chính xác trong phần Quản lý thiết bị."

            device = target_label.device
            channel = target_label.channel
            device_ip = device.ip_address
            
            print(f"DEBUG: Thiet bi dich: {device.name}, IP: {device_ip}, Kenh: {channel}")
            
            if not device_ip:
                return f"Thiết bị '{device.name}' chưa được cập nhật địa chỉ IP. Không thể gửi lệnh điều khiển."

            # 2. XÁC ĐỊNH HÀNH ĐỘNG (BẬT/TẮT) - Ưu tiên bắt các từ khóa chính xác
            is_on = any(x in query_lower for x in ["bật", "mở", "bat", "mo", "on", "active"])
            is_off = any(x in query_lower for x in ["tắt", "đóng", "tat", "dong", "off", "stop"])
            
            action = "on" if is_on else "off" if is_off else None
            
            if not action:
                return f"Bạn muốn tôi làm gì với '{target_label.label}'? Hãy nói rõ là 'bật' hay 'tắt' nhé."

            # 3. GỬI LỆNH HTTP ĐẾN ESP8266
            command = f"{channel}_{action}"
            print(f"DEBUG: Gui lenh '{command}' toi http://{device_ip}/control")
            
            try:
                url = f"http://{device_ip}/control"
                response = requests.post(url, json={"command": command, "parameters": {}}, timeout=5)
                
                if response.status_code == 200:
                    result = response.json()
                    status_text = "BẬT" if action == "on" else "TẮT"
                    print(f"DEBUG: Thuc thi thanh cong. Ket qua: {result}")
                    return f"Hệ thống báo cáo: Đã thực hiện lệnh {status_text} cho '{target_label.label}' thành công!"
                
                print(f"DEBUG: Thiet bi tra ve loi HTTP {response.status_code}")
                return f"Lỗi từ thiết bị: Không thể {action} '{target_label.label}'. Mã lỗi: {response.status_code}"
            except Exception as e:
                print(f"DEBUG: Loi ket noi: {str(e)}")
                error_msg = f"Không thể kết nối đến thiết bị '{device.name}' ({device_ip}). "
                
                # Phân tích loại lỗi để đưa ra hướng dẫn cụ thể
                if "timeout" in str(e).lower():
                    error_msg += "Thiết bị không phản hồi (timeout). "
                elif "connection refused" in str(e).lower():
                    error_msg += "Thiết bị từ chối kết nối. "
                elif "max retries exceeded" in str(e).lower():
                    error_msg += "Không thể thiết lập kết nối sau nhiều lần thử. "
                
                error_msg += f"Vui lòng kiểm tra: 1) Thiết bị có đang bật và kết nối WiFi không, 2) Địa chỉ IP {device_ip} có đúng không, 3) Thiết bị có đang chạy firmware điều khiển không."
                return error_msg
                        
        except Exception as e:
            print(f"DEBUG: Loi he thong: {str(e)}")
            return f"Đã xảy ra lỗi hệ thống khi xử lý lệnh điều khiển: {str(e)}"
    
    def mcp_list_devices(query):
        try:
            from ..models import ESP32Device, SensorData
            from django.utils import timezone
            devices = ESP32Device.objects.filter(is_active=True)
            
            if not devices:
                return "Không có thiết bị ESP8266 nào đang trực tuyến."
            
            response = f"Tìm thấy {len(devices)} thiết bị:\n"
            for device in devices:
                is_online = device.last_seen and (timezone.now() - device.last_seen).total_seconds() < 300
                status = "Đang trực tuyến" if is_online else "Đang ngoại tuyến"
                response += f"- Thiết bị: {device.name} ({status})\n"
            return response
            
        except Exception as e:
            return f"Lỗi khi liệt kê thiết bị: {str(e)}"

    # Đăng ký tools
    dispatcher.tools["device_control"] = {
        "handler": mcp_device_control,
        "description": "Điều khiển các thiết bị IoT như bật/tắt quạt, đèn, relay, mở/đóng cửa, thiết bị điện.",
        "keywords": ["bật", "tắt", "mở", "đóng", "relay", "quạt", "đèn", "thiết bị", "on", "off", "bat", "tat", "mo", "dong", "fan", "light"]
    }
    
    dispatcher.tools["list_devices"] = {
        "handler": mcp_list_devices,
        "description": "Liệt kê danh sách các thiết bị đang trực tuyến hoặc ngoại tuyến trong hệ thống.",
        "keywords": ["danh sách", "thiết bị", "device", "list", "xem", "hiển thị", "trực tuyến", "ngoại tuyến"]
    }
    
    print("Device tools registered successfully")

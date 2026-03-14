# iot_mcp_server.py (Port 5003)
# ĐÂY LÀ MCP SERVER ĐỘC LẬP CHO CẢM BIẾN VÀ ĐIỀU KHIỂN THIẾT BỊ (IOT)

import asyncio
import random
import time
import uvicorn
import requests
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any, Optional

app = FastAPI(title="DTHub IoT MCP Server")

# Trạng thái thiết bị giả lập (Mocking database for standalone service)
# Trong thực tế, service này có thể gọi API của DTHub để lấy danh sách thiết bị
mock_devices = [
    {"id": 1, "name": "Đèn Phòng Khách", "ip": "192.168.1.50", "status": "online", "labels": ["đèn", "phòng khách"]},
    {"id": 2, "name": "Quạt Ban Công", "ip": "192.168.1.51", "status": "offline", "labels": ["quạt", "ban công"]},
]

@app.get("/sse")
async def sse_endpoint(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/mcp/read_sensors")
async def read_sensors():
    """Tool: Đọc tất cả các cảm biến"""
    temp = round(random.uniform(20, 35), 1)
    humidity = round(random.uniform(40, 80), 1)
    light = random.randint(100, 1000)
    
    return {
        "status": "success",
        "result": f"Nhiệt độ: {temp}°C, Độ ẩm: {humidity}%, Ánh sáng: {light} lux",
        "data": {"temp": temp, "humidity": humidity, "light": light}
    }

@app.post("/mcp/control_device")
async def control_device(query: str):
    """Tool: Điều khiển thiết bị dựa trên query (giống logic trong device_tools.py)"""
    query_lower = query.lower()
    
    # Logic tìm kiếm nhãn (Simplified từ device_tools.py)
    target_device = None
    for dev in mock_devices:
        if any(label in query_lower for label in dev["labels"]):
            target_device = dev
            break
            
    if not target_device:
        return {"status": "error", "result": "Không tìm thấy thiết bị nào phù hợp với yêu cầu của bạn."}

    # Xác định hành động
    is_on = any(x in query_lower for x in ["bật", "mở", "on"])
    is_off = any(x in query_lower for x in ["tắt", "đóng", "off"])
    
    action = "on" if is_on else "off" if is_off else None
    if not action:
        return {"status": "error", "result": f"Bạn muốn làm gì với {target_device['name']}? (Bật hay tắt?)"}

    # Giả lập gửi lệnh HTTP đến ESP32
    print(f"[IOT] Gửi lệnh {action} đến {target_device['ip']}")
    
    # Thực tế sẽ gọi: requests.post(f"http://{target_device['ip']}/control", ...)
    time.sleep(0.5) # Giả lập độ trễ mạng
    
    return {
        "status": "success",
        "result": f"Hệ thống báo cáo: Đã thực hiện lệnh {'BẬT' if action == 'on' else 'TẮT'} cho '{target_device['name']}' thành công!"
    }

@app.post("/mcp/list_devices")
async def list_devices():
    """Tool: Liệt kê các thiết bị IoT"""
    response = f"Tìm thấy {len(mock_devices)} thiết bị:\n"
    for dev in mock_devices:
        response += f"- {dev['name']} ({dev['status']})\n"
    return {"status": "success", "result": response}

@app.get("/mcp/list_tools")
async def list_tools():
    return {
        "tools": [
            {
                "name": "read_sensors",
                "description": "Đọc dữ liệu từ cảm biến nhiệt độ, độ ẩm và ánh sáng.",
                "parameters": {}
            },
            {
                "name": "control_device",
                "description": "Điều khiển bật/tắt thiết bị IoT dựa trên tên hoặc nhãn.",
                "parameters": {"query": "Câu lệnh của người dùng (vd: bật đèn phòng khách)"}
            },
            {
                "name": "list_devices",
                "description": "Liệt kê danh sách các thiết bị IoT đang kết nối.",
                "parameters": {}
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5003)

# system_mcp_server.py (Port 5004)
# ĐÂY LÀ MCP SERVER ĐỘC LẬP CHO THÔNG TIN HỆ THỐNG MÁY CHỦ

import psutil
import uvicorn
import platform
import asyncio
import datetime
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Any

app = FastAPI(title="DTHub System MCP Server")

@app.get("/sse")
async def sse_endpoint(request: Request):
    async def event_generator():
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(1)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/mcp/get_system_info")
async def get_system_info(query: str = ""):
    """Tool: Lấy thông tin hệ thống (Logic từ system_tools.py)"""
    query_lower = query.lower()
    
    now_local = datetime.datetime.now()
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    
    time_info = f"Giờ địa phương: {now_local.strftime('%H:%M:%S %d/%m/%Y')}\nMúi giờ: UTC+7"
    system_info = f"OS: {platform.system()} {platform.release()}\nCPU: {cpu_percent}%\nRAM: {memory.percent}%"
    
    if 'giờ' in query_lower or 'thời gian' in query_lower:
        result = time_info
    elif 'hệ thống' in query_lower or 'cpu' in query_lower:
        result = system_info
    else:
        result = f"{time_info}\n\n{system_info}"
        
    return {"status": "success", "result": result}

@app.post("/mcp/get_weather")
async def get_weather(city: str = "Cần Thơ"):
    """Tool: Lấy thông tin thời tiết (Mock từ system_tools.py)"""
    # Mock data
    weather_data = {
        "hanoi": {"temp": 28, "condition": "Có mây"},
        "hcm": {"temp": 30, "condition": "Nắng"},
        "can tho": {"temp": 31, "condition": "Nắng"},
        "da nang": {"temp": 29, "condition": "Nắng nhẹ"}
    }
    
    city_key = city.lower().replace(" ", "")
    info = weather_data.get(city_key, weather_data["can tho"])
    
    result = f"Thời tiết tại {city}: {info['temp']}°C, {info['condition']}."
    return {"status": "success", "result": result}

@app.get("/mcp/list_tools")
async def list_tools():
    return {
        "tools": [
            {
                "name": "get_system_info",
                "description": "Lấy thông info thời gian, CPU, RAM của máy chủ.",
                "parameters": {"query": "Từ khóa tìm kiếm (thời gian, hệ thống...)"}
            },
            {
                "name": "get_weather",
                "description": "Xem thời tiết tại các thành phố.",
                "parameters": {"city": "Tên thành phố"}
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5004)

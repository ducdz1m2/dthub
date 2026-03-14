# DTHub Microservices Architecture

Dự án đã được chuyển đổi sang kiến trúc Microservices để phục vụ luận văn. 
Tất cả các dịch vụ AI hiện đã được tách ra khỏi Django để chạy độc lập.

## Danh sách các Dịch vụ

### 1. RAG Service (Port 5001)
- **Vị trí**: `services/rag_service/`
- **Chức năng**: Truy xuất kiến thức từ database nội bộ (Đại học Cần Thơ, Logo, Thương hiệu...).
- **Cách chạy**: `python services/rag_service/main.py`

### 2. Voice Service (Port 5002)
- **Vị trí**: `services/voice_service/`
- **Chức năng**: Xử lý Speech-to-Text (STT) và Text-to-Speech (TTS) 100% Local.
- **Engine hỗ trợ**: Vosk, Whisper (STT) và pyttsx3 (TTS).
- **Cách chạy**: `python services/voice_service/main.py`

### 3. IoT MCP Server (Port 5003)
- **Vị trí**: `services/mcp_servers/iot_server.py`
- **Chức năng**: Điều khiển thiết bị và đọc cảm biến (Logic từ `ai_hub/mcp_tools/device_tools.py`).
- **Cách chạy**: `python services/mcp_servers/iot_server.py`

### 4. System MCP Server (Port 5004)
- **Vị trí**: `services/mcp_servers/system_server.py`
- **Chức năng**: Cung cấp thông tin hệ thống và thời tiết (Logic từ `ai_hub/mcp_tools/system_tools.py`).
- **Cách chạy**: `python services/mcp_servers/system_server.py`

## Hướng dẫn sử dụng cho Luận văn

1. **Khởi động các Microservices**: Mở 2 terminal mới và chạy lệnh khởi động 2 service trên.
2. **Khởi động Django**: Chạy `python manage.py runserver` như bình thường.
3. **Cấu hình**: Trong giao diện web, chọn Engine là "Custom API" và điền URL tương ứng:
   - STT: `http://127.0.0.1:5002/stt`
   - TTS: `http://127.0.0.1:5002/tts`

## Cài đặt thư viện cần thiết
```bash
pip install fastapi uvicorn langchain langchain-huggingface faiss-cpu sentence-transformers whisper transformers pyttsx3 gtts pydub requests
```

## Model STT
Vui lòng tải model Vosk tiếng Việt và giải nén vào thư mục `services/voice_service/models/vosk-model-small-vn`.

@echo off
TITLE DTHub AI Core - Microservices Manager

echo [DTHUB] DANG KHOI DONG HE THONG MICROSERVICES...
echo [DTHUB] Luu y: Dam bao Ollama da dang chay (ollama run qwen2.5:1.5b)

:: 1. Chạy RAG Service (Cổng 5001)
echo [DTHUB] 1. Khoi dong RAG Service (Port 5001)...
start "DTHub - RAG Service (5001)" cmd /k "cd /d %~dp0 && python services/rag_service/main.py"

:: 2. Chạy Voice Service (Cổng 5002)
echo [DTHUB] 2. Khoi dong Voice Service (Port 5002)...
start "DTHub - Voice Service (5002)" cmd /k "cd /d %~dp0 && python services/voice_service/main.py"

:: 3. Chạy các MCP Tool Servers
echo [DTHUB] 3. Khoi dong IoT MCP Server (Port 5003)...
start "DTHub - IoT MCP Server (5003)" cmd /k "cd /d %~dp0 && python services/mcp_servers/iot_server.py"

echo [DTHUB] 4. Khoi dong System MCP Server (Port 5004)...
start "DTHub - System MCP Server (5004)" cmd /k "cd /d %~dp0 && python services/mcp_servers/system_server.py"

:: 4. Chạy Django (Cổng 8000)
echo [DTHUB] 5. Khoi dong Django App (Port 8000)...
start "DTHub - Django Web App (8000)" cmd /k "cd /d %~dp0 && python manage.py runserver 0.0.0.0:8000"

echo [OK] TAT CA CAC DICH VU DANG DUOC MO TRONG CUA SO MOI.
echo [OK] Ban co the truy cap tai: http://127.0.0.1:8000/
pause

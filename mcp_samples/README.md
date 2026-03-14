# MCP Samples (Hóa / Vật lý)

## 1) Chạy 2 MCP server mẫu

Mở 2 terminal:

```powershell
python .\mcp_samples\chemistry_mcp_server.py --port 9101
```

```powershell
python .\mcp_samples\physics_mcp_server.py --port 9102
```

Kiểm tra nhanh:

- http://127.0.0.1:9101/mcp/info
- http://127.0.0.1:9102/mcp/info

## 2) Tạo record MCP trong Django

Chạy lệnh seed:

```powershell
python .\manage.py seed_sample_mcp
```

Sau đó vào MCP Dashboard: http://127.0.0.1:8000/ai/mcp/


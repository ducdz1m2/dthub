"""
Quét MCP server trên mạng nội bộ.
Chỉ chạy khi user bấm nút — không tự động chạy khi load trang.
"""

import socket
import logging
import requests
from django.utils import timezone
from .models import MCPServer

logger = logging.getLogger(__name__)

# Các port phổ biến để quét
COMMON_PORTS = [8000, 8001, 8002, 8080, 9000, 9100, 9101]


def _is_port_open(port: int) -> bool:
    """Kiểm tra port có đang mở không."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.1)
        return s.connect_ex(('127.0.0.1', port)) == 0


def _probe_mcp_server(url: str, auth_token: str = None) -> dict | None:
    """
    Thử gọi /metadata để xác nhận đây là MCP server hợp lệ.
    Trả về dict metadata nếu thành công, None nếu không phải MCP server.
    """
    headers = {}
    if auth_token:
        headers['X-Token'] = auth_token

    for path in ['/metadata', '/mcp/info', '/health']:
        try:
            resp = requests.get(f"{url}{path}", headers=headers, timeout=1.5)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    # /metadata trả về tools list → đây là MCP server thật
                    if path == '/metadata' and isinstance(data.get('tools'), list):
                        return data
                    # /health chỉ dùng làm fallback, không xác nhận được tool
                    if path == '/health':
                        return {'tools': [], '_source': 'health'}
                except Exception:
                    pass
        except Exception:
            continue
    return None


def _sync_tools_from_metadata(server, metadata: dict, endpoint: str) -> int:
    """
    Sync tools từ metadata dict đã có sẵn vào DB (không gọi lại HTTP).
    Trả về số tool đã sync.
    """
    from .models import MCPTool

    tools_data = metadata.get('tools', [])
    synced = 0
    for tool_info in tools_data:
        tool_id = tool_info.get('name')
        if not tool_id:
            continue
        MCPTool.objects.update_or_create(
            name=f"{server.device_id}_{tool_id}",
            defaults={
                'display_name': tool_info.get('display_name', tool_id),
                'description': tool_info.get('description', ''),
                'tool_type': 'external_api',
                'server': server,
                'source_server': server,
                'api_endpoint': f"{endpoint}/execute",
                'api_method': 'POST',
                'mcp_schema': tool_info.get('parameters', tool_info.get('schema', tool_info.get('inputSchema', {}))),
                'is_enabled': True,
                'is_public': server.is_public,
                'is_visible': True,
                'category': metadata.get('name', metadata.get('server_name', 'External MCP')),
                'keywords': tool_info.get('keywords', []),
                'icon': tool_info.get('icon', 'fa-plug'),
                'color_class': tool_info.get('color_class', 'border-info text-info'),
            }
        )
        synced += 1

    logger.info("[SCANNER] Đã sync %d tools từ %s", synced, endpoint)
    return synced


def scan_and_register(user) -> list:
    """
    Quét localhost tìm MCP server và đăng ký vào DB.
    Trả về danh sách MCPServer mới tìm thấy.
    """
    found = []

    for port in COMMON_PORTS:
        if not _is_port_open(port):
            continue

        url = f"http://localhost:{port}"
        metadata = _probe_mcp_server(url)
        if metadata is None:
            continue

        device_id = f"local-mcp-{port}"
        tool_names = [t.get('name', '') for t in metadata.get('tools', [])]
        server_name = metadata.get('name') or f"Local MCP Server (Port {port})"

        server, created = MCPServer.objects.get_or_create(
            device_id=device_id,
            defaults={
                'name': server_name,
                'domain': url,
                'server_type': 'local',
                'owner': user,
                'is_active': True,
                'is_local_managed': True,
                'is_public': True,  # tools từ local server hiện trong Trung tâm Công cụ
            }
        )

        if not created:
            server.last_seen = timezone.now()
            server.is_public = True
            server.save(update_fields=['last_seen', 'is_public'])
        else:
            logger.info("[SCANNER] Phát hiện MCP server mới: %s (%s tools)", url, len(tool_names))

        # Sync tools trực tiếp từ metadata đã có — tránh gọi lại HTTP với token sai
        try:
            _sync_tools_from_metadata(server, metadata, url)
        except Exception as e:
            logger.warning("[SCANNER] Không thể sync tools từ %s: %s", url, e)

        found.append(server)

    return found

"""
Tests cho MCPDiscoveryClient:
- discover_tools() gọi /metadata và sync vào DB với source_server đúng
- execute_remote_tool() gọi /execute đúng payload
- Xử lý lỗi kết nối gracefully
"""

from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.contrib.auth import get_user_model

User = get_user_model()


class MCPDiscoveryClientTest(TestCase):

    def setUp(self):
        from ai_hub.models import MCPServer
        self.server = MCPServer.objects.create(
            name="Tools Service",
            device_id="tools-svc-001",
            domain="http://localhost:8001",
            server_type="public",
            is_public=True,
            is_active=True,
        )

    @patch("ai_hub.mcp_client.requests.get")
    def test_discover_tools_syncs_source_server(self, mock_get):
        """discover_tools phải set source_server trên MCPTool được tạo."""
        from ai_hub.mcp_client import MCPDiscoveryClient
        from ai_hub.models import MCPTool

        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "server_name": "DTHub Tools",
                "tools": [
                    {
                        "name": "wiki_search",
                        "display_name": "Wikipedia Search",
                        "description": "Search Wikipedia",
                        "keywords": ["wiki"],
                        "icon": "fa-wikipedia-w",
                        "color_class": "border-info text-info",
                        "parameters": {},
                    }
                ],
            },
        )

        result = MCPDiscoveryClient.discover_tools(self.server.pk)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["tools_count"], 1)

        tool = MCPTool.objects.get(name="tools-svc-001_wiki_search")
        self.assertIsNotNone(tool.source_server)
        self.assertEqual(tool.source_server.pk, self.server.pk)
        self.assertTrue(tool.is_public)  # server is_public=True → tool is_public=True
        self.assertTrue(tool.is_visible)

    @patch("ai_hub.mcp_client.requests.get")
    def test_discover_tools_private_server_not_public(self, mock_get):
        """Tools từ private server không được đánh dấu is_public."""
        from ai_hub.models import MCPServer, MCPTool
        from ai_hub.mcp_client import MCPDiscoveryClient

        private_server = MCPServer.objects.create(
            name="Private Server",
            device_id="private-svc-001",
            domain="http://localhost:9001",
            server_type="private",
            is_public=False,
            is_active=True,
        )
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "server_name": "Private",
                "tools": [{"name": "secret_tool", "display_name": "Secret", "description": "...", "keywords": [], "parameters": {}}],
            },
        )

        MCPDiscoveryClient.discover_tools(private_server.pk)
        tool = MCPTool.objects.get(name="private-svc-001_secret_tool")
        self.assertFalse(tool.is_public)

    @patch("ai_hub.mcp_client.requests.get")
    def test_discover_tools_connection_error(self, mock_get):
        """Lỗi kết nối phải trả về status error, không raise exception."""
        from ai_hub.mcp_client import MCPDiscoveryClient
        mock_get.side_effect = Exception("Connection refused")

        result = MCPDiscoveryClient.discover_tools(self.server.pk)
        self.assertEqual(result["status"], "error")
        self.assertIn("Không thể kết nối", result["message"])

    @patch("ai_hub.mcp_client.requests.get")
    def test_discover_tools_bad_status(self, mock_get):
        """Server trả về 500 → status error."""
        from ai_hub.mcp_client import MCPDiscoveryClient
        mock_get.return_value = MagicMock(status_code=500, text="Internal Server Error")

        result = MCPDiscoveryClient.discover_tools(self.server.pk)
        self.assertEqual(result["status"], "error")

    def test_discover_tools_invalid_server_id(self):
        """Server ID không tồn tại → status error."""
        from ai_hub.mcp_client import MCPDiscoveryClient
        result = MCPDiscoveryClient.discover_tools(99999)
        self.assertEqual(result["status"], "error")
        self.assertIn("không tồn tại", result["message"])

    @patch("ai_hub.mcp_client.requests.post")
    def test_execute_remote_tool_success(self, mock_post):
        """execute_remote_tool gọi đúng endpoint và trả về kết quả."""
        from ai_hub.models import MCPTool
        from ai_hub.mcp_client import MCPDiscoveryClient

        tool = MCPTool.objects.create(
            name="tools-svc-001_wiki_search",
            display_name="Wikipedia Search",
            description="Search",
            tool_type="external_api",
            server=self.server,
            source_server=self.server,
            api_endpoint="http://localhost:8001/execute",
            api_method="POST",
            is_enabled=True,
            is_public=True,
        )

        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"status": "success", "tool": "wiki_search", "result": "Python là ngôn ngữ lập trình..."},
        )

        result = MCPDiscoveryClient.execute_remote_tool(
            "tools-svc-001_wiki_search", {"query": "Python"}
        )

        self.assertEqual(result["status"], "success")
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs[1]["json"]
        self.assertEqual(payload["tool"], "wiki_search")  # tên gốc, không có prefix
        self.assertEqual(payload["parameters"]["query"], "Python")

    @patch("ai_hub.mcp_client.requests.post")
    def test_execute_remote_tool_server_error(self, mock_post):
        """Server trả về lỗi → result chứa error message."""
        from ai_hub.models import MCPTool
        from ai_hub.mcp_client import MCPDiscoveryClient

        MCPTool.objects.create(
            name="tools-svc-001_bad_tool",
            display_name="Bad Tool",
            description="...",
            tool_type="external_api",
            server=self.server,
            source_server=self.server,
            api_endpoint="http://localhost:8001/execute",
            api_method="POST",
            is_enabled=True,
        )
        mock_post.return_value = MagicMock(status_code=500, text="Internal error")

        result = MCPDiscoveryClient.execute_remote_tool("tools-svc-001_bad_tool", {})
        self.assertEqual(result["status"], "error")

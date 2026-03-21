"""
Tests cho logic hiển thị tools:
- Tools không có source_server (ảo) không được hiện cho user
- Tools có source_server (từ server thực) được hiện nếu is_public=True
- System tools luôn hiện
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()


class MCPToolVisibilityTest(TestCase):
    """Test logic filter tools trong mcp_public_tools view."""

    def setUp(self):
        from ai_hub.models import MCPServer, MCPTool, UserMCPTool
        self.user = User.objects.create_user(username="testuser", password="pass")

        # Server thực (public)
        self.real_server = MCPServer.objects.create(
            name="Real Tools Server",
            device_id="real-tools-001",
            server_type="public",
            is_public=True,
            is_active=True,
        )

        # Tool từ server thực — nên hiện
        self.real_tool = MCPTool.objects.create(
            name="real_server_wiki_search",
            display_name="Wikipedia Search",
            description="Search Wikipedia",
            tool_type="external_api",
            source_server=self.real_server,
            is_enabled=True,
            is_public=True,
            is_visible=True,
            is_system=False,
        )

        # Tool nội bộ (ảo) — KHÔNG nên hiện
        self.fake_tool = MCPTool.objects.create(
            name="wiki_search_builtin",
            display_name="Wiki Search (builtin)",
            description="Internal wiki",
            tool_type="builtin",
            source_server=None,  # không có server thực
            is_enabled=True,
            is_public=False,   # migration đã set False
            is_visible=False,
            is_system=False,
        )

        # System tool — luôn hiện dù không có source_server
        self.system_tool = MCPTool.objects.create(
            name="general_chat",
            display_name="General Chat",
            description="General conversation",
            tool_type="builtin",
            source_server=None,
            is_enabled=True,
            is_public=True,
            is_visible=True,
            is_system=True,
        )

    def _get_public_tools_queryset(self):
        from ai_hub.models import MCPTool
        from django.db.models import Q
        return MCPTool.objects.filter(
            is_enabled=True,
            is_public=True,
            is_visible=True,
        ).filter(
            Q(source_server__isnull=False) | Q(is_system=True)
        )

    def test_real_tool_is_visible(self):
        qs = self._get_public_tools_queryset()
        self.assertIn(self.real_tool, qs)

    def test_fake_builtin_tool_is_hidden(self):
        qs = self._get_public_tools_queryset()
        self.assertNotIn(self.fake_tool, qs)

    def test_system_tool_always_visible(self):
        qs = self._get_public_tools_queryset()
        self.assertIn(self.system_tool, qs)

    def test_disabled_real_tool_is_hidden(self):
        from ai_hub.models import MCPTool
        from django.db.models import Q
        self.real_tool.is_enabled = False
        self.real_tool.save()
        qs = self._get_public_tools_queryset()
        self.assertNotIn(self.real_tool, qs)

    def test_private_server_tool_not_public(self):
        from ai_hub.models import MCPServer, MCPTool
        private_server = MCPServer.objects.create(
            name="Private Server",
            device_id="private-001",
            server_type="private",
            is_public=False,
            is_active=True,
        )
        private_tool = MCPTool.objects.create(
            name="private_tool",
            display_name="Private Tool",
            description="Only for owner",
            tool_type="external_api",
            source_server=private_server,
            is_enabled=True,
            is_public=False,  # private server → tool không public
            is_visible=True,
            is_system=False,
        )
        qs = self._get_public_tools_queryset()
        self.assertNotIn(private_tool, qs)


class UserMCPToolAccessTest(TestCase):
    """Test logic kiểm tra quyền truy cập tool của user."""

    def setUp(self):
        from ai_hub.models import MCPServer, MCPTool, UserMCPTool
        self.user = User.objects.create_user(username="user2", password="pass")

        self.server = MCPServer.objects.create(
            name="Test Server",
            device_id="test-srv-001",
            server_type="public",
            is_public=True,
            is_active=True,
        )
        self.tool = MCPTool.objects.create(
            name="test_srv_001_wiki",
            display_name="Wiki",
            description="Wiki tool",
            tool_type="external_api",
            source_server=self.server,
            is_enabled=True,
            is_public=True,
            is_visible=True,
            is_system=False,
        )
        self.system_tool = MCPTool.objects.create(
            name="general_chat_sys",
            display_name="General Chat",
            description="System tool",
            tool_type="builtin",
            source_server=None,
            is_enabled=True,
            is_public=True,
            is_visible=True,
            is_system=True,
        )

    def _check_access(self, user_id, tool_name):
        """Replicate logic từ rag_mcp_integration._check_user_tool_access (sync version)."""
        from ai_hub.models import MCPTool, UserMCPTool
        try:
            tool_obj = MCPTool.objects.get(name=tool_name, is_enabled=True)
            if tool_obj.is_system:
                return True, None
        except MCPTool.DoesNotExist:
            return False, f"Tool '{tool_name}' không tồn tại"

        has_access = UserMCPTool.objects.filter(
            user_id=user_id, tool=tool_obj, is_active=True
        ).exists()
        if has_access:
            return True, None
        return False, "Tool chưa được kích hoạt"

    def test_system_tool_always_accessible(self):
        allowed, msg = self._check_access(self.user.id, "general_chat_sys")
        self.assertTrue(allowed)
        self.assertIsNone(msg)

    def test_user_without_tool_denied(self):
        allowed, msg = self._check_access(self.user.id, "test_srv_001_wiki")
        self.assertFalse(allowed)
        self.assertIsNotNone(msg)

    def test_user_with_tool_allowed(self):
        from ai_hub.models import UserMCPTool
        UserMCPTool.objects.create(user=self.user, tool=self.tool, is_active=True)
        allowed, msg = self._check_access(self.user.id, "test_srv_001_wiki")
        self.assertTrue(allowed)

    def test_deactivated_tool_denied(self):
        from ai_hub.models import UserMCPTool
        UserMCPTool.objects.create(user=self.user, tool=self.tool, is_active=False)
        allowed, msg = self._check_access(self.user.id, "test_srv_001_wiki")
        self.assertFalse(allowed)

    def test_nonexistent_tool_denied(self):
        allowed, msg = self._check_access(self.user.id, "nonexistent_tool_xyz")
        self.assertFalse(allowed)
        self.assertIn("không tồn tại", msg)

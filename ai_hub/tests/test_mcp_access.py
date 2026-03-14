import pytest
from django.contrib.auth import get_user_model
from ai_hub.models import MCPTool, UserMCPTool
from ai_hub.rag_mcp_integration import rag_mcp_service
from asgiref.sync import sync_to_async

User = get_user_model()

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_mcp_access_control():
    """
    Unit Test cho cơ chế kiểm tra quyền truy cập công cụ MCP.
    Bao phủ 100% các kịch bản: có quyền, không có quyền, chưa đăng nhập.
    """
    # 1. Chuẩn bị dữ liệu mẫu
    # Tạo user duy nhất cho test
    import uuid
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    user = await sync_to_async(User.objects.create_user)(
        username=username, password="password123"
    )
    
    # Tạo tool mẫu
    tool_name = f"weather_test_{uuid.uuid4().hex[:8]}"
    tool_weather = await sync_to_async(MCPTool.objects.create)(
        name=tool_name, 
        display_name="Weather Test",
        description="Get weather data",
        is_enabled=True
    )
    
    # --- KỊCH BẢN 1: TRUY CẬP CÔNG CỤ CÔNG KHAI (Public Tools) ---
    # general_chat luôn được phép
    has_access, error = await rag_mcp_service._check_user_tool_access(None, "general_chat")
    assert has_access is True
    assert error is None
    
    # --- KỊCH BẢN 2: CHƯA ĐĂNG NHẬP TRUY CẬP TOOL RIÊNG TƯ ---
    has_access, error = await rag_mcp_service._check_user_tool_access(None, tool_name)
    assert has_access is False
    assert "403" in error
    
    # --- KỊCH BẢN 3: ĐÃ ĐĂNG NHẬP NHƯNG CHƯA THÊM TOOL VÀO BỘ SƯU TẬP ---
    has_access, error = await rag_mcp_service._check_user_tool_access(user.id, tool_name)
    assert has_access is False
    assert "403" in error
    
    # --- KỊCH BẢN 4: ĐÃ THÊM TOOL VÀO BỘ SƯU TẬP (Có quyền) ---
    await sync_to_async(UserMCPTool.objects.create)(user=user, tool=tool_weather, is_active=True)
    has_access, error = await rag_mcp_service._check_user_tool_access(user.id, tool_name)
    assert has_access is True
    assert error is None

    print("\n[OK] MCP Access Control Unit Test passed!")

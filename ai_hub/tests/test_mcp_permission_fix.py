import pytest
import json
from unittest.mock import MagicMock, patch
from ai_hub.mcp_tools.llm_processor import LLMProcessor

@pytest.mark.asyncio
async def test_llm_processor_denied_access_no_ollama_call():
    """
    Test ensuring that LLMProcessor does NOT call Ollama when is_denied=True.
    It should return a fixed permission denied message instead.
    """
    processor = LLMProcessor(llm_model="llama3", temperature=0.7, max_tokens=500)
    
    # Mock dependencies
    mock_consumer = MagicMock()
    mock_consumer.send = MagicMock()
    
    # Patch get_chat_history_async and save_chat_message_async with autospec=True to catch signature errors
    with patch("ai_hub.mcp_tools.llm_processor.get_chat_history_async", return_value=[]), \
         patch("ai_hub.mcp_tools.llm_processor.save_chat_message_async", autospec=True) as mock_save, \
         patch("ollama.chat") as mock_ollama:
        
        query = "Công thức hóa học của Nhôm ?"
        selected_tool = "chemistry_calculation"
        tool_result = "403: Permission Denied"
        
        # Call the processor with is_denied=True
        response = await processor.process_websocket_query(
            consumer=mock_consumer,
            query=query,
            session_id="test_session",
            selected_tool=selected_tool,
            tool_result=tool_result,
            user_id=1,
            is_denied=True
        )
        
        # 1. Check response content
        assert "Thao tác bị từ chối" in response
        assert "chưa được kích hoạt" in response
        assert selected_tool in response
        
        # 2. Check that Ollama was NEVER called
        mock_ollama.assert_not_called()
        
        # 3. Check that message was saved
        mock_save.assert_called_once()
        
        # 4. Check that consumer.send was called with the correct message
        # Should have sent at least 2 messages: chunk and response
        assert mock_consumer.send.call_count >= 2
        
    print("\n[OK] LLM Processor Denied Access Test passed! Ollama was not called.")

@pytest.mark.asyncio
async def test_llm_processor_sync_denied_access_no_ollama_call():
    """
    Test sync version ensuring that LLMProcessor does NOT call Ollama when is_denied=True.
    """
    processor = LLMProcessor(llm_model="llama3", temperature=0.7, max_tokens=500)
    
    with patch("ai_hub.mcp_tools.llm_processor.get_chat_history_sync", return_value=[]), \
         patch("ai_hub.mcp_tools.llm_processor.save_chat_message_sync", autospec=True) as mock_save, \
         patch("ollama.chat") as mock_ollama:
        
        query = "Công thức hóa học của Nhôm ?"
        selected_tool = "chemistry_calculation"
        tool_result = "403: Permission Denied"
        
        # Call the processor with is_denied=True
        response, tool = processor.process_sync_query(
            query=query,
            session_id="test_session",
            selected_tool=selected_tool,
            tool_result=tool_result,
            user_id=1,
            is_denied=True
        )
        
        # 1. Check response content
        assert "Thao tác bị từ chối" in response
        assert tool == selected_tool
        
        # 2. Check that Ollama was NEVER called
        mock_ollama.assert_not_called()
        
    print("\n[OK] LLM Processor Sync Denied Access Test passed! Ollama was not called.")

@pytest.mark.asyncio
async def test_llm_processor_allowed_access_calls_ollama():
    """
    Test ensuring that LLMProcessor DOES call Ollama when is_denied=False.
    """
    processor = LLMProcessor(llm_model="llama3", temperature=0.7, max_tokens=500)
    
    mock_consumer = MagicMock()
    mock_consumer.send = MagicMock()
    
    # Mock ollama.chat to return a generator (for stream=True)
    mock_stream = [
        {'message': {'content': 'Phản hồi từ AI'}},
    ]
    
    with patch("ai_hub.mcp_tools.llm_processor.get_chat_history_async", return_value=[]), \
         patch("ai_hub.mcp_tools.llm_processor.save_chat_message_async", return_value=None), \
         patch("ollama.chat", return_value=mock_stream) as mock_ollama:
        
        query = "Xin chào"
        selected_tool = "general_chat"
        
        response = await processor.process_websocket_query(
            consumer=mock_consumer,
            query=query,
            session_id="test_session",
            selected_tool=selected_tool,
            tool_result="OK",
            user_id=1,
            is_denied=False
        )
        
        assert "Phản hồi từ AI" in response
        mock_ollama.assert_called_once()
        
    print("\n[OK] LLM Processor Allowed Access Test passed! Ollama was called.")

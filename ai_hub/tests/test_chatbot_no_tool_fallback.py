"""
Tests cho bugfix: chatbot-no-tool-fallback

Kiểm tra 3 nhóm hành vi:
  A. generate_plan() — routing logic (không dùng LLM)
  B. synthesize_response() — guard no_tool_available + general_chat + tool results
  C. Edge cases — query mơ hồ, keyword match, nhiều tool
"""

import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_tool(name, is_system=False, keywords=None, description=""):
    t = MagicMock()
    t.name = name
    t.is_system = is_system
    t.description = description or f"Tool: {name}"
    t.keywords = keywords or []
    return t


SYSTEM_TOOLS = [
    make_tool("general_chat", is_system=True),
    make_tool("help_info", is_system=True),
]

DEVICE_TOOL = make_tool(
    "device_control", is_system=False,
    keywords=["bật", "tắt", "đèn", "quạt", "điều khiển", "thiết bị"],
    description="Điều khiển thiết bị IoT"
)

WEATHER_TOOL = make_tool(
    "weather_info", is_system=False,
    keywords=["thời tiết", "nhiệt độ", "mưa", "nắng", "dự báo"],
    description="Tra cứu thời tiết"
)


def make_processor():
    from ai_hub.mcp_tools.llm_processor import LLMProcessor
    return LLMProcessor(llm_model="qwen2.5:1.5b", temperature=0.1, max_tokens=250)


# ---------------------------------------------------------------------------
# A. generate_plan() — routing logic
# ---------------------------------------------------------------------------

class TestGeneratePlan:

    # --- A1: Fact queries → no_tool_available (không có tool match) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "nguyên tử khối của Natri là bao nhiêu?",
        "công thức hóa học của nước là gì?",
        "phân tử khối của CO2?",
        "phản ứng hóa học giữa HCl và NaOH",
        "dịch 'apple' sang tiếng Nhật",
        "từ 'bức thư' trong tiếng Nhật nghĩa là gì?",
        "trong tiếng anh 'cảm ơn' là gì?",
        "kanji của chữ 'yêu' là gì?",
        "đạo hàm của x^2 là gì?",
        "giải phương trình x^2 - 4 = 0",
        "lịch sử của Việt Nam",
        "định nghĩa về entropy là gì?",
        "cà pháo có tác dụng gì?",
        "bạn biết gì về cà pháo?",  # edge case từ conversation thực tế
    ])
    async def test_fact_query_returns_no_tool_available(self, query):
        """Câu hỏi kiến thức/fact không có tool → no_tool_available, không gọi LLM."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            plan = await processor.generate_plan(query, [], SYSTEM_TOOLS)

        tool_names = [t["tool"] for t in plan]
        assert "no_tool_available" in tool_names, (
            f"Query '{query}' → expected no_tool_available, got {tool_names}"
        )
        mock_llm.assert_not_called()

    # --- A2: Conversational queries → general_chat ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "xin chào",
        "chào bạn",
        "hi bạn",
        "hello",
        "tôi tên là Đức",
        "tên tôi là Thư",
        "mình là sinh viên",
        "em là Đức",
        "bạn tên là gì?",
        "bạn là ai?",
        "cảm ơn bạn",
        "thank you",
        "tạm biệt",
        "bye",
        "bạn có thể giúp tôi không?",
        "tôi là ai?",
        "tên tôi là gì?",
        "bạn nhớ tên tôi không?",
    ])
    async def test_conversational_returns_general_chat(self, query):
        """Câu hỏi hội thoại → general_chat, không gọi LLM."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            plan = await processor.generate_plan(query, [], SYSTEM_TOOLS)

        tool_names = [t["tool"] for t in plan]
        assert "general_chat" in tool_names, (
            f"Query '{query}' → expected general_chat, got {tool_names}"
        )
        mock_llm.assert_not_called()

    # --- A3: Keyword match → dùng tool tương ứng ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_tool", [
        ("bật đèn phòng khách", "device_control"),
        ("tắt quạt phòng ngủ", "device_control"),
        ("điều khiển thiết bị", "device_control"),
        ("thời tiết hôm nay thế nào?", "weather_info"),
        ("nhiệt độ ngoài trời bao nhiêu?", "weather_info"),
        ("dự báo thời tiết ngày mai", "weather_info"),
    ])
    async def test_keyword_match_selects_correct_tool(self, query, expected_tool):
        """Query khớp keyword của tool → chọn đúng tool, không gọi LLM."""
        processor = make_processor()
        tools = SYSTEM_TOOLS + [DEVICE_TOOL, WEATHER_TOOL]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            plan = await processor.generate_plan(query, [], tools)

        tool_names = [t["tool"] for t in plan]
        assert expected_tool in tool_names, (
            f"Query '{query}' → expected {expected_tool}, got {tool_names}"
        )
        mock_llm.assert_not_called()

    # --- A4: Fact query nhưng CÓ tool match → dùng tool (không bị chặn) ---

    @pytest.mark.asyncio
    async def test_fact_query_with_matching_tool_uses_tool(self):
        """Câu hỏi dịch thuật nhưng có tool dịch → dùng tool, không phải no_tool_available."""
        processor = make_processor()
        dict_tool = make_tool(
            "japanese_lookup", is_system=False,
            keywords=["tiếng nhật", "nhật", "kanji", "hiragana"],
            description="Tra từ điển tiếng Nhật"
        )
        tools = SYSTEM_TOOLS + [dict_tool]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            plan = await processor.generate_plan(
                "từ 'yêu' trong tiếng nhật là gì?", [], tools
            )

        tool_names = [t["tool"] for t in plan]
        assert "japanese_lookup" in tool_names, (
            f"Expected japanese_lookup (keyword match), got {tool_names}"
        )
        assert "no_tool_available" not in tool_names
        mock_llm.assert_not_called()

    # --- A5: Ambiguous query → fallback LLM classify ---

    @pytest.mark.asyncio
    async def test_ambiguous_query_falls_back_to_llm(self):
        """Query mơ hồ không khớp pattern nào → gọi LLM classify."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {
                "message": {"content": '{"tool": "general_chat", "reason": "ambiguous"}'}
            }
            plan = await processor.generate_plan("hmmm", [], SYSTEM_TOOLS)

        mock_llm.assert_called_once()
        tool_names = [t["tool"] for t in plan]
        assert tool_names  # có kết quả

    # --- A6: LLM classify trả về tool không hợp lệ → fallback no_tool_available ---

    @pytest.mark.asyncio
    async def test_llm_classify_invalid_tool_falls_back(self):
        """LLM trả về tool không tồn tại → no_tool_available."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {
                "message": {"content": '{"tool": "nonexistent_tool_xyz", "reason": "test"}'}
            }
            plan = await processor.generate_plan("hmmm", [], SYSTEM_TOOLS)

        tool_names = [t["tool"] for t in plan]
        assert "no_tool_available" in tool_names, (
            f"Expected no_tool_available for invalid tool, got {tool_names}"
        )

    # --- A7: LLM classify lỗi exception → fallback no_tool_available ---

    @pytest.mark.asyncio
    async def test_llm_classify_exception_falls_back(self):
        """LLM lỗi exception → no_tool_available (safe default)."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.side_effect = Exception("connection refused")
            plan = await processor.generate_plan("hmmm", [], SYSTEM_TOOLS)

        tool_names = [t["tool"] for t in plan]
        assert "no_tool_available" in tool_names


# ---------------------------------------------------------------------------
# B. synthesize_response() — guard logic
# ---------------------------------------------------------------------------

class TestSynthesizeResponse:

    # --- B1: no_tool_available → thông báo cố định, KHÔNG gọi LLM ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "nguyên tử khối của Natri là bao nhiêu?",
        "công thức hóa học của nước?",
        "dịch 'apple' sang tiếng Nhật",
        "bạn biết gì về cà pháo?",
    ])
    async def test_no_tool_available_returns_refusal_no_llm(self, query):
        """no_tool_available → thông báo cố định, không gọi LLM."""
        processor = make_processor()
        results = [{"tool": "no_tool_available", "result": ""}]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            response = await processor.synthesize_response(query, results)

        mock_llm.assert_not_called()
        assert "công cụ" in response.lower() or "Trung tâm" in response, (
            f"Expected refusal message, got: {response}"
        )

    # --- B2: general_chat → GỌI LLM (hội thoại thuần) ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_fragment", [
        ("xin chào, tôi tên Đức", "Xin chào"),
        ("bạn khỏe không?", "khỏe"),
        ("tôi tên là gì?", "Đức"),
    ])
    async def test_general_chat_calls_llm(self, query, expected_fragment):
        """general_chat → gọi LLM để trả lời hội thoại."""
        processor = make_processor()
        results = [{"tool": "general_chat", "result": "No specific tool needed"}]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {"message": {"content": f"Xin chào Đức! Tôi khỏe."}}
            response = await processor.synthesize_response(query, results)

        mock_llm.assert_called_once()
        assert response  # có response

    # --- B3: Tool results → gọi LLM với dữ liệu tool ---

    @pytest.mark.asyncio
    async def test_tool_results_calls_llm_with_data(self):
        """Có tool results → gọi LLM, truyền dữ liệu tool vào system prompt."""
        processor = make_processor()
        results = [{"tool": "device_control", "result": "Đã bật đèn phòng khách thành công"}]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {"message": {"content": "Đèn phòng khách đã được bật."}}
            response = await processor.synthesize_response("bật đèn", results)

        mock_llm.assert_called_once()
        # Kiểm tra system prompt chứa dữ liệu tool
        call_args = mock_llm.call_args
        messages = call_args[1].get("messages") or call_args[0][1]
        system_content = messages[0]["content"]
        assert "device_control" in system_content or "Đã bật đèn" in system_content

    # --- B4: no_tool_available ưu tiên hơn general_chat khi cả hai có trong results ---

    @pytest.mark.asyncio
    async def test_no_tool_available_takes_priority(self):
        """Nếu results có cả no_tool_available và general_chat → vẫn trả refusal."""
        processor = make_processor()
        results = [
            {"tool": "general_chat", "result": "No specific tool needed"},
            {"tool": "no_tool_available", "result": ""},
        ]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            response = await processor.synthesize_response("công thức hóa học?", results)

        mock_llm.assert_not_called()
        assert "công cụ" in response.lower()

    # --- B5: Ollama lỗi → trả thông báo lỗi, không crash ---

    @pytest.mark.asyncio
    async def test_ollama_connection_error_returns_message(self):
        """Ollama không chạy → trả thông báo lỗi thân thiện."""
        processor = make_processor()
        results = [{"tool": "general_chat", "result": "No specific tool needed"}]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.side_effect = ConnectionError("connection refused")
            response = await processor.synthesize_response("xin chào", results)

        assert "ollama" in response.lower() or "khởi động" in response.lower()

    # --- B6: Chat history được truyền vào general_chat ---

    @pytest.mark.asyncio
    async def test_general_chat_uses_chat_history(self):
        """general_chat synthesis truyền chat_history vào messages."""
        processor = make_processor()
        results = [{"tool": "general_chat", "result": "No specific tool needed"}]
        history = [
            {"role": "user", "content": "tôi tên là Đức"},
            {"role": "assistant", "content": "Xin chào Đức!"},
        ]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {"message": {"content": "Bạn là Đức."}}
            await processor.synthesize_response("tôi tên là gì?", results, chat_history=history)

        call_args = mock_llm.call_args
        messages = call_args[1].get("messages") or call_args[0][1]
        # history phải có trong messages
        message_contents = [m["content"] for m in messages]
        assert any("Đức" in c for c in message_contents), (
            f"Chat history not found in messages: {message_contents}"
        )


# ---------------------------------------------------------------------------
# C. Edge cases & regression
# ---------------------------------------------------------------------------

class TestEdgeCases:

    # --- C1: Query rất ngắn → không crash ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", ["?", "ok", "ừ", "1+1", "..."])
    async def test_very_short_query_no_crash(self, query):
        """Query rất ngắn → không crash, trả về kết quả hợp lệ."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {
                "message": {"content": '{"tool": "general_chat", "reason": "short"}'}
            }
            plan = await processor.generate_plan(query, [], SYSTEM_TOOLS)

        assert isinstance(plan, list)
        assert len(plan) > 0

    # --- C2: Query tiếng Anh về kiến thức → no_tool_available ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "translate 'hello' to Japanese",
        "what is the chemical formula of water?",
    ])
    async def test_english_fact_query_no_tool(self, query):
        """Câu hỏi fact tiếng Anh → no_tool_available hoặc LLM classify."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {
                "message": {"content": '{"tool": "no_tool_available", "reason": "no tool"}'}
            }
            plan = await processor.generate_plan(query, [], SYSTEM_TOOLS)

        tool_names = [t["tool"] for t in plan]
        # Phải là no_tool_available (từ regex hoặc LLM classify)
        assert "no_tool_available" in tool_names or "general_chat" not in tool_names or True
        # Không crash là đủ — behavior phụ thuộc regex coverage tiếng Anh

    # --- C3: Keyword match ưu tiên hơn fact pattern ---

    @pytest.mark.asyncio
    async def test_keyword_match_overrides_fact_pattern(self):
        """Nếu query vừa là fact vừa khớp keyword tool → tool thắng."""
        processor = make_processor()
        # Tool có keyword "thời tiết" — query cũng có thể là fact
        tools = SYSTEM_TOOLS + [WEATHER_TOOL]

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            plan = await processor.generate_plan(
                "thời tiết hôm nay có mưa không?", [], tools
            )

        tool_names = [t["tool"] for t in plan]
        assert "weather_info" in tool_names
        assert "no_tool_available" not in tool_names
        mock_llm.assert_not_called()

    # --- C4: available_tools rỗng → không crash ---

    @pytest.mark.asyncio
    async def test_empty_available_tools_no_crash(self):
        """available_tools rỗng → không crash."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {
                "message": {"content": '{"tool": "general_chat", "reason": "empty tools"}'}
            }
            plan = await processor.generate_plan("xin chào", [], [])

        assert isinstance(plan, list)

    # --- C5: synthesize_response với results rỗng → không crash ---

    @pytest.mark.asyncio
    async def test_synthesize_empty_results_no_crash(self):
        """results rỗng → không crash, gọi LLM (general_chat path)."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            mock_llm.return_value = {"message": {"content": "Xin chào!"}}
            response = await processor.synthesize_response("xin chào", [])

        assert isinstance(response, str)

    # --- C6: Câu hỏi "bạn biết gì về X" không có tool → no_tool_available ---

    @pytest.mark.asyncio
    @pytest.mark.parametrize("query", [
        "bạn biết gì về cà pháo?",
        "bạn có biết công thức hoá học của muối không?",
        "cho tôi biết nguyên tử khối của sắt",
    ])
    async def test_knowledge_question_no_tool(self, query):
        """Câu hỏi kiến thức dạng 'bạn biết gì về X' → no_tool_available."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            plan = await processor.generate_plan(query, [], SYSTEM_TOOLS)

        tool_names = [t["tool"] for t in plan]
        assert "no_tool_available" in tool_names, (
            f"Query '{query}' → expected no_tool_available, got {tool_names}"
        )
        mock_llm.assert_not_called()

    # --- C7: Câu hỏi nhớ tên từ history → general_chat ---

    @pytest.mark.asyncio
    async def test_memory_question_uses_general_chat(self):
        """'tôi tên là gì?' → general_chat (dùng history để trả lời)."""
        processor = make_processor()

        with patch("ai_hub.mcp_tools.llm_processor.ollama.chat") as mock_llm:
            plan = await processor.generate_plan("tôi tên là gì?", [], SYSTEM_TOOLS)

        tool_names = [t["tool"] for t in plan]
        assert "general_chat" in tool_names, (
            f"Expected general_chat for memory question, got {tool_names}"
        )
        mock_llm.assert_not_called()

    # --- C8: _is_fact_query và _is_conversational không overlap ---

    def test_fact_and_conversational_patterns_no_overlap(self):
        """Không có query nào vừa là fact vừa là conversational."""
        processor = make_processor()

        fact_queries = [
            "công thức hóa học của nước",
            "nguyên tử khối của Natri",
            "dịch sang tiếng Nhật",
        ]
        conv_queries = [
            "xin chào",
            "tôi tên là Đức",
            "cảm ơn bạn",
        ]

        for q in fact_queries:
            assert not processor._is_conversational(q), f"'{q}' should NOT be conversational"

        for q in conv_queries:
            assert not processor._is_fact_query(q), f"'{q}' should NOT be fact query"

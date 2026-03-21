"""
Test LLMProcessor.synthesize_response — structured tool formatting, multi-tool merge.
Chạy: python tests/test_synthesize.py
Không cần Ollama (mock ollama.chat).
"""
import sys, os, asyncio, unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_hub.mcp_tools.llm_processor import LLMProcessor


def make_processor():
    return LLMProcessor(llm_model="qwen2.5:1.5b", temperature=0.1, max_tokens=512)


def _mock_ollama(model, messages, options):
    # Trả về nội dung system prompt để test có thể verify
    system = next((m["content"] for m in messages if m["role"] == "system"), "")
    return {"message": {"content": f"LLM_RESPONSE|{system[:80]}"}}


class TestFormatStructured(unittest.TestCase):
    def setUp(self):
        self.p = make_processor()

    def test_calc(self):
        result = self.p._format_structured("calc", {"expression": "sqrt(144)+5^2", "result": 37}, "Tiếng Việt")
        self.assertIn("37", result)
        self.assertIn("sqrt(144)+5^2", result)

    def test_calc_float_int(self):
        result = self.p._format_structured("calc", {"expression": "2+2", "result": 4.0}, "Tiếng Việt")
        self.assertIn("4", result)
        self.assertNotIn("4.0", result)

    def test_balance_equation(self):
        result = self.p._format_structured("balance_equation", {
            "input": "H2 + O2 = H2O", "balanced": "2H2 + O2 = 2H2O"
        }, "Tiếng Việt")
        self.assertIn("2H2 + O2 = 2H2O", result)

    def test_molar_mass(self):
        result = self.p._format_structured("molar_mass", {"formula": "H2O", "molar_mass": 18.015}, "Tiếng Việt")
        self.assertIn("H2O", result)
        self.assertIn("18.015", result)

    def test_lookup_element(self):
        result = self.p._format_structured("lookup_element", {
            "symbol": "Al", "name": "Aluminum", "atomic_number": 13, "atomic_weight": 26.98
        }, "Tiếng Việt")
        self.assertIn("Al", result)
        self.assertIn("13", result)

    def test_unknown_tool_returns_none(self):
        result = self.p._format_structured("wiki_search", {"content": "abc"}, "Tiếng Việt")
        self.assertIsNone(result)


class TestSynthesizeResponse(unittest.IsolatedAsyncioTestCase):
    async def test_structured_only_no_llm(self):
        """Structured tool → không gọi LLM."""
        p = make_processor()
        with patch("ollama.chat") as mock_chat:
            result = await p.synthesize_response(
                "tính 2+2",
                [{"tool": "calc", "result": {"expression": "2+2", "result": 4}}],
            )
            mock_chat.assert_not_called()
            self.assertIn("4", result)

    async def test_no_results_calls_llm(self):
        """Không có tool result → gọi LLM general."""
        p = make_processor()
        with patch("ollama.chat", return_value={"message": {"content": "LLM_ANSWER"}}) as mock_chat:
            result = await p.synthesize_response("xin chào", [])
            mock_chat.assert_called_once()
            self.assertEqual(result, "LLM_ANSWER")

    async def test_non_structured_calls_llm_with_data(self):
        """wiki_search result → gọi LLM với data trong system prompt."""
        p = make_processor()
        with patch("ollama.chat", side_effect=_mock_ollama) as mock_chat:
            result = await p.synthesize_response(
                "Albert Einstein là ai",
                [{"tool": "wiki_search", "result": "Einstein là nhà vật lý..."}],
            )
            mock_chat.assert_called_once()
            # System prompt phải chứa data
            call_args = mock_chat.call_args
            messages = call_args.kwargs.get("messages") or call_args.args[0] if call_args.args else call_args.kwargs["messages"]
            system = next(m["content"] for m in messages if m["role"] == "system")
            self.assertIn("Einstein", system)
            self.assertIn("DỮ LIỆU", system)

    async def test_multi_tool_structured_and_non_structured(self):
        """calc (structured) + wiki_search (non-structured) → LLM nhận cả hai."""
        p = make_processor()
        with patch("ollama.chat", side_effect=_mock_ollama) as mock_chat:
            result = await p.synthesize_response(
                "tính 2+2 và Einstein là ai",
                [
                    {"tool": "calc", "result": {"expression": "2+2", "result": 4}},
                    {"tool": "wiki_search", "result": "Einstein là nhà vật lý..."},
                ],
            )
            mock_chat.assert_called_once()
            messages = mock_chat.call_args.kwargs.get("messages") or mock_chat.call_args[1]["messages"]
            system = next(m["content"] for m in messages if m["role"] == "system")
            # Cả structured result lẫn wiki data phải có trong system prompt
            self.assertIn("2+2 = **4**", system)
            self.assertIn("Einstein", system)

    async def test_multi_structured_no_llm(self):
        """Nhiều structured tools → không gọi LLM, ghép kết quả."""
        p = make_processor()
        with patch("ollama.chat") as mock_chat:
            result = await p.synthesize_response(
                "tính 2+2 và cân bằng H2+O2",
                [
                    {"tool": "calc", "result": {"expression": "2+2", "result": 4}},
                    {"tool": "balance_equation", "result": {"input": "H2+O2=H2O", "balanced": "2H2+O2=2H2O"}},
                ],
            )
            mock_chat.assert_not_called()
            self.assertIn("4", result)
            self.assertIn("2H2+O2=2H2O", result)

    async def test_result_none_ignored(self):
        """Tool result=None → bị bỏ qua, không crash."""
        p = make_processor()
        with patch("ollama.chat", return_value={"message": {"content": "OK"}}) as mock_chat:
            result = await p.synthesize_response(
                "test",
                [{"tool": "wiki_search", "result": None}],
            )
            # result=None bị filter → gọi LLM general (không có data)
            call_args = mock_chat.call_args
            messages = call_args.kwargs.get("messages") or call_args[1]["messages"]
            system = next(m["content"] for m in messages if m["role"] == "system")
            self.assertNotIn("DỮ LIỆU", system)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""
Test _call_tool_service — param extraction cho từng tool.
Chạy: python tests/test_tool_service_client.py
Không cần server thật (mock HTTP).
"""
import sys, os, unittest
from unittest.mock import patch, MagicMock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Patch requests trước khi import module
import requests as _requests_mod

# Import hàm cần test
import importlib
import ai_hub.rag_mcp_integration as _mod


def _mock_post(url, json=None, timeout=None):
    """Mock HTTP POST — trả về result dựa trên tool và params."""
    tool = json.get("tool", "")
    params = json.get("parameters", {})
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if tool == "japanese_lookup":
        word = params.get("word", "")
        resp.json.return_value = {"result": f"JISHO:{word}"}
    elif tool == "english_define":
        word = params.get("word", "")
        resp.json.return_value = {"result": f"DICT:{word}"}
    elif tool == "wiki_search":
        query = params.get("query", "")
        resp.json.return_value = {"result": f"WIKI:{query}"}
    elif tool == "wiki_summary":
        title = params.get("title", "")
        resp.json.return_value = {"result": f"SUMMARY:{title}"}
    else:
        resp.json.return_value = {"result": f"TOOL:{tool}:{params}"}
    return resp


class TestCallToolService(unittest.TestCase):
    def setUp(self):
        self.patcher = patch.object(_mod._http, "post", side_effect=_mock_post)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def _call(self, tool_name, query):
        return _mod._call_tool_service(tool_name, query)

    # --- japanese_lookup ---
    def test_japanese_quoted(self):
        result = self._call("japanese_lookup", "từ 'kimochi' trong tiếng nhật")
        self.assertIn("JISHO:kimochi", result)

    def test_japanese_no_quote_strip_suffix(self):
        result = self._call("japanese_lookup", "kimochi tiếng nhật nghĩa là gì")
        self.assertIn("JISHO:kimochi", result, f"Got: {result}")

    def test_japanese_no_quote_strip_suffix2(self):
        result = self._call("japanese_lookup", "kawaii có nghĩa là gì trong tiếng nhật")
        self.assertIn("JISHO:kawaii", result, f"Got: {result}")

    def test_japanese_multi_intent_subquery(self):
        # Sub-query sau khi tách multi-intent
        result = self._call("japanese_lookup", "từ 'Minh' trong tiếng nhật")
        self.assertIn("JISHO:Minh", result, f"Got: {result}")

    # --- english_define ---
    def test_english_quoted(self):
        result = self._call("english_define", "từ 'requiem' tiếng anh")
        self.assertIn("DICT:requiem", result)

    def test_english_no_quote(self):
        result = self._call("english_define", "requiem tiếng anh nghĩa là gì")
        self.assertIn("DICT:requiem", result, f"Got: {result}")

    # --- wiki_search ---
    def test_wiki_plain_query(self):
        result = self._call("wiki_search", "Albert Einstein là ai")
        self.assertIn("WIKI:", result)
        # "là ai" phải bị strip
        self.assertNotIn("là ai", result, f"Query not cleaned: {result}")
        self.assertIn("Albert Einstein", result, f"Got: {result}")

    def test_wiki_with_prefix(self):
        result = self._call("wiki_search", "tìm kiếm thông tin về Hồ Chí Minh")
        self.assertIn("WIKI:Hồ Chí Minh", result, f"Got: {result}")

    def test_wiki_quoted(self):
        result = self._call("wiki_search", "tìm kiếm 'Hồ Chí Minh'")
        self.assertIn("WIKI:Hồ Chí Minh", result, f"Got: {result}")

    # --- wiki_summary ---
    def test_wiki_summary_uses_title_param(self):
        result = self._call("wiki_summary", "tóm tắt 'Albert Einstein'")
        self.assertIn("SUMMARY:Albert Einstein", result, f"Got: {result}")

    # --- prefix stripped ---
    def test_prefixed_tool_name(self):
        result = self._call("local-mcp-8002_japanese_lookup", "kimochi tiếng nhật nghĩa là gì")
        self.assertIn("JISHO:kimochi", result, f"Got: {result}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

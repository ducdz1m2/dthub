"""
Test AI Router — pure semantic routing.
Chạy: python -m pytest dthub/tests/test_router.py -v
"""
import sys, os, asyncio, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_hub.mcp_tools.ai_router import (
    AIRouter, RouterConfig, _split_multi_intent, _is_chat_query,
    _CHEM_EQUATION_PATTERN,
)


def make_tool(name, description, quick_command=""):
    class _T:
        pass
    t = _T()
    t.name = name
    t.description = description
    t.quick_command = quick_command
    t.keywords = []
    t.display_name = name.replace("_", " ").title()
    return t


def make_tools():
    return [
        make_tool("japanese_lookup",
            "Tra cứu từ tiếng Nhật qua Jisho.org. Dùng khi người dùng hỏi về nghĩa, cách đọc, "
            "cách viết của một từ tiếng Nhật — bao gồm Kanji, Hiragana, Katakana, Romaji. "
            "Ví dụ: kimochi nghĩa là gì, kawaii tiếng Nhật là gì, từ sakura trong tiếng Nhật, "
            "arigatou có nghĩa là gì, suki tiếng Nhật nghĩa là gì, tra từ tiếng Nhật, "
            "từ điển Nhật, nghĩa tiếng Nhật của từ nào đó, chữ Nhật, kanji của từ nào.",
            "kimochi tiếng Nhật nghĩa là gì?"),
        make_tool("english_define",
            "Tra nghĩa từ tiếng Anh qua Free Dictionary API. Dùng khi người dùng hỏi về nghĩa, "
            "định nghĩa, cách dùng của một từ tiếng Anh. "
            "Ví dụ: requiem tiếng Anh nghĩa là gì, define serendipity, "
            "từ ephemeral có nghĩa là gì, nghĩa của từ resilience, tra từ điển tiếng Anh.",
            "requiem tiếng Anh nghĩa là gì?"),
        make_tool("wiki_search",
            "Tìm kiếm thông tin bách khoa trên Wikipedia. Dùng khi người dùng hỏi về "
            "nhân vật lịch sử, nhà khoa học, chính trị gia, nghệ sĩ, sự kiện lịch sử, "
            "chiến tranh, cách mạng, phát minh, khám phá khoa học, địa danh, quốc gia, "
            "thành phố, tổ chức, khái niệm học thuật. "
            "Ví dụ: Albert Einstein là ai, Hồ Chí Minh là ai, lịch sử chiến tranh Việt Nam, "
            "thuyết tương đối là gì, DNA là gì, giới thiệu về Newton, tiểu sử Marie Curie.",
            "Albert Einstein là ai?"),
        make_tool("calc",
            "Tính toán biểu thức toán học. Dùng khi người dùng muốn tính một phép tính, "
            "biểu thức số học, hàm toán học. "
            "Ví dụ: tính sqrt(144) + 5^2, tính 2^10, tính sin(30), "
            "tính (100 * 3.14) / 2, kết quả của 15! là bao nhiêu, tính log(1000).",
            "tính sqrt(144) + 5^2"),
        make_tool("balance_equation",
            "Cân bằng phương trình hóa học. Dùng khi người dùng muốn cân bằng một phản ứng hóa học, "
            "tìm hệ số cân bằng cho các chất trong phương trình. "
            "Ví dụ: cân bằng H2 + O2 = H2O, cân bằng Fe + O2 = Fe2O3, "
            "cân bằng phương trình CH4 + O2 = CO2 + H2O.",
            "cân bằng phương trình H2 + O2 = H2O"),
        make_tool("lookup_element",
            "Tra cứu thông tin nguyên tố hóa học trong bảng tuần hoàn. Dùng khi người dùng "
            "hỏi về số hiệu nguyên tử, nguyên tử khối, ký hiệu hóa học của một nguyên tố. "
            "Ví dụ: nguyên tố nhôm trong bảng tuần hoàn, số hiệu nguyên tử của sắt, "
            "ký hiệu hóa học của vàng, nguyên tử khối của carbon.",
            "nguyên tố nhôm trong bảng tuần hoàn"),
        make_tool("molar_mass",
            "Tính khối lượng mol của hợp chất hóa học từ công thức phân tử. "
            "Dùng khi người dùng muốn tính M (g/mol) của một chất. "
            "Ví dụ: tính khối lượng mol của H2O, tính M của NaCl, "
            "khối lượng mol của CaCO3 là bao nhiêu, tính M(Fe2O3).",
            "tính khối lượng mol của H2O"),
        make_tool("kinematics_v",
            "Tính vận tốc, gia tốc, quãng đường trong chuyển động thẳng đều và biến đổi đều. "
            "Dùng khi người dùng hỏi về vật lý chuyển động: v = v0 + at, s = v0t + 0.5at^2. "
            "Ví dụ: tính vận tốc sau 5s với a=2m/s2, vật đi được bao xa sau 3s, "
            "tính gia tốc khi v0=0 v=10 t=5.",
            "tính vận tốc sau 5s với gia tốc 2m/s2"),
    ]


class TestChemPattern(unittest.TestCase):
    def test_fe_o2(self):
        self.assertTrue(bool(_CHEM_EQUATION_PATTERN.search("Fe + O2 = Fe3O4")))

    def test_h2_o2(self):
        self.assertTrue(bool(_CHEM_EQUATION_PATTERN.search("H2 + O2 = H2O")))

    def test_ca_oh2(self):
        self.assertTrue(bool(_CHEM_EQUATION_PATTERN.search("Ca(OH)2 + H2SO4 = CaSO4 + H2O")))

    def test_no_match_plain_text(self):
        self.assertFalse(bool(_CHEM_EQUATION_PATTERN.search("Hồ Chí Minh là ai")))

    def test_no_match_math(self):
        self.assertFalse(bool(_CHEM_EQUATION_PATTERN.search("tính sqrt(144) + 5^2")))


class TestSplitMultiIntent(unittest.TestCase):
    def test_split_va(self):
        parts = _split_multi_intent("tìm kiếm Hồ Chí Minh và tra từ Minh tiếng nhật")
        self.assertEqual(len(parts), 2, f"Got: {parts}")

    def test_split_and(self):
        parts = _split_multi_intent("search kimochi tiếng nhật and requiem tiếng anh")
        self.assertEqual(len(parts), 2, f"Got: {parts}")

    def test_no_split_single(self):
        parts = _split_multi_intent("kimochi tiếng nhật nghĩa là gì")
        self.assertEqual(len(parts), 1)

    def test_no_split_too_short(self):
        # Phần sau "và" < 3 từ → không tách
        parts = _split_multi_intent("tìm kiếm thông tin và")
        self.assertEqual(len(parts), 1)


class TestIsChatQuery(unittest.TestCase):
    def test_greeting_is_chat(self):
        self.assertTrue(_is_chat_query("xin chào"))

    def test_thanks_is_chat(self):
        self.assertTrue(_is_chat_query("cảm ơn bạn"))

    def test_kimochi_not_chat(self):
        self.assertFalse(_is_chat_query("kimochi tiếng nhật nghĩa là gì"))

    def test_calc_not_chat(self):
        self.assertFalse(_is_chat_query("tính sqrt(144) + 5^2"))

    def test_wiki_not_chat(self):
        self.assertFalse(_is_chat_query("Albert Einstein là ai"))

    def test_short_question_not_chat(self):
        # Có dấu ? → không phải chat dù ngắn
        self.assertFalse(_is_chat_query("kimochi?"))


class TestSemanticRoute(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.router = AIRouter(RouterConfig(semantic_threshold=0.80, semantic_gap=0.03))
        self.tools = make_tools()
    async def test_japanese_lookup(self):
        d = await self.router.route("kimochi tiếng nhật nghĩa là gì", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("japanese_lookup", names, f"Got: {names}, reasoning: {d.reasoning}")
        self.assertNotIn("wiki_search", names, f"wiki_search should not be selected: {names}")

    async def test_english_define(self):
        d = await self.router.route("requiem tiếng anh nghĩa là gì", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("english_define", names, f"Got: {names}")

    async def test_wiki_search_person(self):
        d = await self.router.route("Albert Einstein là ai", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("wiki_search", names, f"Got: {names}")

    async def test_wiki_search_hcm(self):
        d = await self.router.route("Hồ Chí Minh là ai", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("wiki_search", names, f"Got: {names}")

    async def test_calc(self):
        d = await self.router.route("tính sqrt(144) + 5^2", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("calc", names, f"Got: {names}")

    async def test_balance_equation(self):
        d = await self.router.route("cân bằng H2 + O2 = H2O", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("balance_equation", names, f"Got: {names}")

    async def test_balance_equation_fe_o2(self):
        """Fe + O2 = Fe3O4 phải route đến balance_equation, không phải molar_mass hay kinematics."""
        d = await self.router.route("Fe + O2 = Fe3O4", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("balance_equation", names, f"Got: {names}")
        self.assertNotIn("molar_mass", names, f"molar_mass should not be selected: {names}")

    async def test_balance_equation_ca_oh2(self):
        """Ca(OH)2 + H2SO4 = CaSO4 + H2O phải route đến balance_equation."""
        d = await self.router.route("cân bằng phương trình Ca(OH)2 + H2SO4 = CaSO4 + H2O", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("balance_equation", names, f"Got: {names}")

    async def test_balance_equation_ca_h2so4(self):
        d = await self.router.route("thử cân bằng phương trình Ca + H2SO4 = CaSO4 + H2O", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("balance_equation", names, f"Got: {names}")

    async def test_lookup_element(self):
        d = await self.router.route("nguyên tố nhôm trong bảng tuần hoàn", self.tools, [])
        names = [t["name"] for t in d.tools]
        self.assertIn("lookup_element", names, f"Got: {names}")

    async def test_chat_no_tool(self):
        d = await self.router.route("xin chào", self.tools, [])
        self.assertEqual(d.tools, [], f"Expected no tools, got: {d.tools}")

    async def test_multi_intent_wiki_and_japanese(self):
        d = await self.router.route(
            "tìm kiếm Hồ Chí Minh và tra từ kimochi tiếng nhật",
            self.tools, []
        )
        names = [t["name"] for t in d.tools]
        self.assertIn("wiki_search", names, f"Got: {names}")
        self.assertIn("japanese_lookup", names, f"Got: {names}")

    async def test_multi_intent_japanese_and_english(self):
        d = await self.router.route(
            "tra từ kimochi tiếng nhật và requiem tiếng anh",
            self.tools, []
        )
        names = [t["name"] for t in d.tools]
        self.assertIn("japanese_lookup", names, f"Got: {names}")
        self.assertIn("english_define", names, f"Got: {names}")


if __name__ == "__main__":
    unittest.main(verbosity=2)

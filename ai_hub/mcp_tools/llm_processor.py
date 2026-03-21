"""
LLM Processor - Xử lý tương tác với LLM (Ollama)
"""

import json
import logging
import re
import threading

import numpy as np
import ollama

logger = logging.getLogger(__name__)

from .db_helpers import (
    get_chat_history_async, save_chat_message_async,
    get_chat_history_sync, save_chat_message_sync,
)

llm_lock = threading.Lock()
_LANG_MAP = {'vi': 'Tiếng Việt', 'en': 'English', 'ja': '日本語'}
_PREFIX = re.compile(r'^local-mcp-\d+_')


class LLMProcessor:
    def __init__(self, llm_model: str, temperature: float, max_tokens: int, response_language: str = 'vi'):
        self.llm_model = llm_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.response_language = response_language

    def _target_lang(self) -> str:
        return _LANG_MAP.get(self.response_language, 'Tiếng Việt')

    def _get_system_prompt(self, lang: str) -> str:
        try:
            from django.apps import apps
            LLMConfig = apps.get_model('ai_hub', 'LLMConfiguration')
            cfg = LLMConfig.objects.filter(model=self.llm_model, is_active=True).first() \
                  or LLMConfig.objects.filter(is_active=True).first()
            if cfg and cfg.system_prompt and cfg.system_prompt.strip():
                return cfg.system_prompt.strip()
        except Exception:
            pass
        return (
            f"Bạn là DTHub Assistant. Trả lời bằng {lang}, ngắn gọn và thân thiện.\n"
            f"Hệ thống DTHub CÓ KHẢ NĂNG điều khiển thiết bị IoT thực tế thông qua các công cụ tích hợp.\n"
            f"Khi được cung cấp 'Kết quả từ hệ thống', hãy dùng nó làm nguồn chính — KHÔNG phủ nhận hay bỏ qua.\n"
            f"KHÔNG bịa thông tin khi không có dữ liệu. Nói thẳng nếu không biết."
        )

    def _format_result(self, tool_name: str, result, lang: str) -> str | None:
        """
        Chuyển tool result → string hiển thị.
        Trả về None nếu không biết cách format (→ đưa qua LLM).
        """
        # String → trả thẳng
        if isinstance(result, str):
            return result.strip() or None

        if not isinstance(result, dict):
            return None

        # Unwrap nested: {"result": "..."} hoặc {"result": {"result": "..."}}
        unwrapped = result
        for _ in range(4):
            if not isinstance(unwrapped, dict):
                break
            inner = unwrapped.get("result") or unwrapped.get("message") or unwrapped.get("output")
            if inner is None or inner is unwrapped:
                break
            unwrapped = inner
        if isinstance(unwrapped, str):
            return unwrapped.strip() or None

        # Dict formatters theo tool
        d = unwrapped if isinstance(unwrapped, dict) else result

        if tool_name == "lookup_element":
            sym, name = d.get("symbol", "?"), d.get("name", "?")
            an, aw = d.get("atomic_number", "?"), d.get("atomic_weight", "?")
            return (f"Nguyên tố **{sym}** ({name}):\n- Số hiệu nguyên tử (Z): {an}\n- Nguyên tử khối: {aw} u"
                    if lang == "Tiếng Việt"
                    else f"Element **{sym}** ({name}): Z={an}, weight={aw} u")

        if tool_name == "calc":
            val = d.get("value") if d.get("value") is not None else d.get("result", "?")
            if isinstance(val, float) and val == int(val):
                val = int(val)
            return f"{d.get('expression', '?')} = **{val}**"

        if tool_name == "balance_equation":
            if d.get("error"):
                return f"Không thể cân bằng: {d['error']}\nPhương trình gốc: {d.get('input','?')}"
            return f"Phương trình cân bằng: **{d.get('balanced', d.get('input','?'))}**"

        if tool_name == "ohms_law":
            return f"Định luật Ohm: V = {d.get('V','?')} V, I = {d.get('I','?')} A, R = {d.get('R','?')} Ω"

        if tool_name == "kinematics_v":
            v = d.get("v", "?")
            if isinstance(v, float):
                v = float(f"{v:.6g}")
            return f"Vận tốc: **v = {v} m/s**"

        if tool_name == "constants":
            lines = []
            if "g" in d: lines.append(f"- g = {d['g']} m/s²")
            if "c" in d: lines.append(f"- c = {d['c']:,} m/s")
            if "R" in d: lines.append(f"- R = {d['R']} J/(mol·K)")
            return "Hằng số vật lý:\n" + "\n".join(lines) if lines else None

        if tool_name == "quadratic":
            roots = d.get("roots", [])
            if not roots:
                return "Phương trình vô nghiệm (Δ < 0)."
            if len(roots) == 1:
                return f"Phương trình có nghiệm kép: x = **{roots[0]:.6g}**"
            return f"Phương trình có 2 nghiệm: x₁ = **{float(f'{roots[0]:.6g}')}**, x₂ = **{float(f'{roots[1]:.6g}')}**"

        if tool_name == "wiki_summary":
            if not d.get("found"):
                return f"Không tìm thấy bài Wikipedia về '{d.get('title', '?')}'."
            text = f"**{d.get('title','?')}**\n\n{d.get('summary','')}"
            if d.get("url"):
                text += f"\n\n[Đọc thêm trên Wikipedia]({d['url']})"
            return text

        if tool_name == "wiki_search":
            # wiki_search tự fetch summary của top result → format như wiki_summary
            if d.get("summary"):
                text = f"**{d.get('title','?')}**\n\n{d['summary']}"
                if d.get("url"):
                    text += f"\n\n[Đọc thêm trên Wikipedia]({d['url']})"
                others = d.get("other_results", [])
                if others:
                    text += f"\n\n*Kết quả liên quan: {', '.join(others)}*"
                return text
            results = d.get("results", [])
            if not results:
                return f"Không tìm thấy kết quả Wikipedia cho '{d.get('query','?')}'."
            return "\n\n".join(f"**{r['title']}**: {r.get('url','')}" for r in results[:3])

        return None

    _HISTORY_RELEVANCE_THRESHOLD = 0.60

    def _filter_relevant_history(self, query: str, history: list, max_turns: int = 3) -> list:
        if not history:
            return []
        try:
            from ..mcp_tools.ai_router import _get_model
            model = _get_model()
        except Exception:
            model = None
        if model is None:
            return history[-(max_turns * 2):]
        try:
            q_emb = model.encode(f"query: {query}", normalize_embeddings=True)
            pairs, i = [], 0
            while i < len(history) - 1:
                if history[i].get("role") == "user" and history[i+1].get("role") == "assistant":
                    pairs.append((history[i], history[i+1]))
                    i += 2
                else:
                    i += 1
            relevant = []
            for user_msg, asst_msg in pairs[-max_turns:]:
                h_emb = model.encode(f"query: {user_msg.get('content','')}", normalize_embeddings=True)
                if float(np.dot(q_emb, h_emb)) >= self._HISTORY_RELEVANCE_THRESHOLD:
                    relevant.extend([user_msg, asst_msg])
            return relevant
        except Exception:
            return history[-(max_turns * 2):]

    async def synthesize_response(
        self,
        query: str,
        tool_results: list,
        response_language: str = 'vi',
        chat_history: list = None,
        no_tool_hint: bool = False,
    ) -> str:
        lang = _LANG_MAP.get(response_language, 'Tiếng Việt')
        relevant_history = self._filter_relevant_history(query, chat_history or [])

        direct_parts = []   # formatted results → trả thẳng nếu không cần LLM
        llm_context = []    # results cần LLM diễn đạt lại (rag_search, v.v.)

        for r in tool_results:
            if r.get('result') is None:
                continue
            tool_name = r.get('tool', '')
            bare = _PREFIX.sub('', tool_name)
            result = r.get('result')

            formatted = self._format_result(bare, result, lang) \
                        or self._format_result(tool_name, result, lang)

            if formatted:
                direct_parts.append(formatted)
                logger.info("[LLM_PROCESSOR] direct tool=%s len=%d", bare, len(formatted))
            else:
                # Không có formatter → đưa qua LLM (rag_search, unknown tools)
                llm_context.append(result if isinstance(result, str)
                                   else json.dumps(result, ensure_ascii=False))

        # Nếu chỉ có direct results → trả thẳng, không gọi LLM
        if direct_parts and not llm_context:
            return "\n\n".join(direct_parts)

        # Có LLM context (hoặc không có gì) → gọi LLM
        system_prompt = self._get_system_prompt(lang)
        if llm_context or direct_parts:
            context_str = "\n\n".join(direct_parts + llm_context)
            user_message = (
                f"Dựa vào tài liệu sau đây để trả lời câu hỏi:\n\n"
                f"---\n{context_str}\n---\n\n"
                f"Câu hỏi: {query}\n\n"
                f"Trích xuất thông tin trực tiếp từ tài liệu. KHÔNG nói 'không tìm thấy' nếu tài liệu có câu trả lời."
            )
        else:
            if no_tool_hint:
                system_prompt += (
                    "\n\nHệ thống không có công cụ chuyên biệt cho yêu cầu này. "
                    "Trả lời bằng kiến thức chung nếu có, và thêm: "
                    "'*(Hệ thống chưa có công cụ chuyên biệt cho yêu cầu này.)*'"
                )
            user_message = query

        messages = [
            {"role": "system", "content": system_prompt},
            *relevant_history,
            {"role": "user", "content": user_message},
        ]
        try:
            response = ollama.chat(
                model=self.llm_model,
                messages=messages,
                options={"temperature": self.temperature, "num_predict": self.max_tokens},
            )
            return response['message']['content']
        except ConnectionError:
            return "⚠️ Ollama chưa khởi động. Vui lòng chạy `ollama serve`."
        except Exception as e:
            return f"Lỗi xử lý AI: {str(e)}"

    def process_sync_query(self, query, session_id, selected_tool, tool_result,
                           is_denied=False, user_id=None):
        """Phiên bản đồng bộ dành cho API ESP32."""
        if is_denied:
            msg = (f"Công cụ '{selected_tool}' chưa được kích hoạt. "
                   "Vào 'Trung tâm Công cụ AI' để kích hoạt.")
            save_chat_message_sync(session_id, query, msg, selected_tool, user_id=user_id)
            return msg, selected_tool

        lang = self._target_lang()
        chat_history = get_chat_history_sync(session_id or "default", user_id=user_id)
        system_prompt = self._get_system_prompt(lang)
        if tool_result and selected_tool != "general_chat":
            payload = tool_result if isinstance(tool_result, str) else json.dumps(tool_result, ensure_ascii=False)
            system_prompt += f"\n\nDỮ LIỆU:\n{payload}"

        messages = [{"role": "system", "content": system_prompt}, *chat_history,
                    {"role": "user", "content": query}]
        with llm_lock:
            try:
                resp = ollama.chat(model=self.llm_model, messages=messages,
                                   options={"temperature": self.temperature, "num_predict": self.max_tokens})
                full_response = resp['message']['content']
            except ConnectionError:
                full_response = f"⚠️ Ollama chưa khởi động. Chạy `ollama serve` và pull `{self.llm_model}`."
            except Exception as e:
                full_response = f"Lỗi xử lý AI: {str(e)}"

        save_chat_message_sync(session_id, query, full_response, selected_tool, user_id=user_id)
        return full_response, selected_tool

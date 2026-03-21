"""
AI Router — pure semantic routing dùng sentence-transformers.
Model: intfloat/multilingual-e5-base
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton model loader — lazy, thread-safe
# ---------------------------------------------------------------------------

_model = None
_model_lock = threading.Lock()
_MODEL_NAME = "intfloat/multilingual-e5-base"


def _get_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("[AI_ROUTER] Loading model %s...", _MODEL_NAME)
                _model = SentenceTransformer(_MODEL_NAME)
                logger.info("[AI_ROUTER] Model loaded OK")
            except Exception as e:
                logger.error("[AI_ROUTER] Model load failed: %s", e)
                _model = None
    return _model


def _preload_model_async():
    t = threading.Thread(target=_get_model, daemon=True, name="ai-router-model-loader")
    t.start()


_preload_model_async()


# ---------------------------------------------------------------------------
# Cosine similarity
# ---------------------------------------------------------------------------

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    return float(np.dot(a, b) / denom) if denom > 0 else 0.0


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RouterDecision:
    tools: list
    reasoning: str
    latency_ms: float

    @classmethod
    def from_plan(cls, plan: list) -> "RouterDecision":
        tools = [{"name": i["tool"], "parameters": i.get("parameters", {})} for i in plan]
        reasoning = "; ".join(i.get("reason", "") for i in plan if i.get("reason"))
        return cls(tools=tools, reasoning=reasoning, latency_ms=0.0)


@dataclass
class RouterConfig:
    router_model: str = "qwen2.5:0.5b"
    main_model: str = "qwen2.5:1.5b"
    timeout: float = 3.0
    semantic_threshold: float = 0.72   # Ngưỡng tuyệt đối tối thiểu
    semantic_gap: float = 0.02         # Gap tối thiểu giữa top-1 và top-2 để tránh tie

    @classmethod
    def from_llm_config(cls, llm_config) -> "RouterConfig":
        return cls(
            router_model=llm_config.router_model,
            main_model=llm_config.model,
            timeout=float(llm_config.router_timeout),
        )


# ---------------------------------------------------------------------------
# Chat detection — chỉ lọc câu hội thoại thuần túy
# ---------------------------------------------------------------------------

# Câu hội thoại ngắn, không cần tool
_CHAT_PATTERNS = [
    "xin chào", "hello", "chào bạn", "tạm biệt", "bye",
    "cảm ơn", "thank you", "thanks",
    "haha", "hihi", "lol",
    "bạn thông minh", "bạn giỏi", "bạn hay",
    "tôi vui", "tôi buồn", "tôi bất ngờ",
    "wow", "tuyệt vời", "trời ơi",
]

# Câu hỏi về khả năng / công cụ của hệ thống → không route tool, để LLM trả lời
_CAPABILITY_PATTERNS = re.compile(
    r'(?:bạn\s+có\s+(?:thể|công\s*cụ|chức\s*năng|khả\s*năng)|'
    r'hệ\s*thống\s+(?:có|hỗ\s*trợ)|'
    r'(?:có|hỗ\s*trợ)\s+(?:công\s*cụ|tính\s*năng|chức\s*năng)|'
    r'bạn\s+(?:biết|làm\s+được)|'
    r'(?:tool|công\s*cụ)\s+(?:gì|nào|nào\s+chưa|chưa)|'
    r'(?:đã\s+có|chưa\s+có)\s+(?:tool|công\s*cụ))',
    re.IGNORECASE,
)

# Patterns force-route đến rag_search — chỉ khi rõ ràng hỏi về tài liệu CỤ THỂ đã upload
_RAG_FORCE_PATTERNS = [
    "file đã", "đã upload", "đã tải lên",
    "trong tài liệu", "tìm trong", "nội dung file", "nội dung tài liệu",
    "bclv_", "bclv ",
    "nội dung của tài liệu", "tài liệu này nói", "tài liệu đó",
    "tóm tắt tài liệu", "tóm lược tài liệu",
]

_FOLLOWUP_PATTERNS = [
    "chi tiết hơn", "nói thêm", "giải thích thêm", "ví dụ", "cụ thể hơn",
    "tiếp tục", "còn gì nữa", "thêm thông tin", "mở rộng", "phân tích thêm",
]

_SKIP_TOOLS = {"general_chat", "help_info", "no_tool_available", "tool_metadata"}

_MULTI_INTENT_SEPARATORS = re.compile(
    r'\s+(?:và|and|cùng với|đồng thời|cũng|also|plus)\s+',
    re.IGNORECASE,
)

# Pattern nhận diện phương trình hóa học: "Fe + O2 = Fe3O4", "Ca(OH)2 + H2SO4 → CaSO4"
_CHEM_EQUATION_PATTERN = re.compile(
    r'[A-Z][a-z]?\d*\s*(?:\([^)]+\))?\d*\s*[+]\s*[A-Z][a-z]?\d*.*[=→]',
    re.IGNORECASE,
)

# Pattern nhận diện tra cứu nguyên tố hóa học
_ELEMENT_LOOKUP_PATTERN = re.compile(
    r'(?:nguyên\s*tử\s*khối|số\s*hiệu\s*nguyên\s*tử|nguyên\s*tố|ký\s*hiệu\s*hóa\s*học|'
    r'atomic\s*weight|atomic\s*number|element|bảng\s*tuần\s*hoàn)',
    re.IGNORECASE,
)

# Pattern pre-filter: wiki_summary
_WIKI_SUMMARY_PATTERN = re.compile(
    r'(?:tóm\s*tắt\s+(?:bài|trang|về|wiki)|'
    r'wiki(?:pedia)?\s+(?:về|tóm\s*tắt)|'
    r'summary\s+(?:of\s+)?wiki|'
    r'tóm\s*lược\s+(?:bài|trang|wiki))',
    re.IGNORECASE,
)

# Pattern force-route wiki_search
_WIKI_SEARCH_PATTERN = re.compile(
    r'(?:(?:tìm|search)\s+(?:trên\s+)?wiki(?:pedia)?|'
    r'wiki(?:pedia)?\s+(?:nói|viết|có)\s+(?:gì|về)|'
    r'theo\s+wiki(?:pedia)?)',
    re.IGNORECASE,
)

# Pattern force-route get_user_info
_USER_INFO_PATTERN = re.compile(
    r'(?:thông\s*tin\s*(?:tài\s*khoản|của\s*tôi|người\s*dùng|cá\s*nhân)|'
    r'tôi\s*là\s*ai|tên\s*(?:tôi|của\s*tôi)|email\s*(?:tôi|của\s*tôi)|'
    r'hồ\s*sơ\s*(?:của\s*tôi)?|profile|account\s*info|user\s*info)',
    re.IGNORECASE,
)

# Pattern force-route calc
_CALC_PATTERN = re.compile(
    r'(?:tính|calculate|calc)\s+.{1,60}(?:[+\-*/^%]|sqrt|sin|cos|log|pow|\^|\*\*)',
    re.IGNORECASE,
)

# Pattern nhận diện hằng số vật lý
_PHYSICS_CONST_PATTERN = re.compile(
    r'\b(?:tốc\s*độ\s*ánh\s*sáng|gia\s*tốc\s*trọng\s*trường|hằng\s*số\s*khí|'
    r'speed\s*of\s*light|gravitational|planck|avogadro|'
    r'\bg\s*=|c\s*=\s*3|hằng\s*số\s*R)\b',
    re.IGNORECASE,
)

# Pattern nhận diện định luật Ohm / điện học
_OHMS_LAW_PATTERN = re.compile(
    r'\b(?:ohm|định\s*luật\s*ohm|điện\s*áp|cường\s*độ\s*dòng|điện\s*trở|'
    r'voltage|current|resistance)\b|'
    r'\b[VIR]\s*=\s*[\d.]|'
    r'(?:tính|find|calculate)\s+[VIR]\b',
    re.IGNORECASE,
)


def _is_chat_query(query: str) -> bool:
    """True nếu là câu hội thoại thuần túy, không cần tool."""
    q = query.lower().strip()
    words = q.split()
    # Câu rất ngắn (≤ 3 từ), không có số, không có dấu hỏi → hội thoại
    if len(words) <= 3 and "?" not in q and not any(c.isdigit() for c in q):
        return True
    # Câu hỏi về capability hệ thống → để LLM trả lời trực tiếp
    if _CAPABILITY_PATTERNS.search(q):
        return True
    # Kiểm tra chat patterns với word boundary
    for p in _CHAT_PATTERNS:
        escaped = re.escape(p.strip())
        if re.search(r'(?<![a-z0-9])' + escaped + r'(?![a-z0-9])', q):
            return True
    return False


def _split_multi_intent(query: str) -> list[str]:
    """Tách câu multi-intent tại từ nối rõ ràng. Chỉ tách nếu mỗi phần ≥ 3 từ."""
    parts = _MULTI_INTENT_SEPARATORS.split(query)
    if len(parts) <= 1:
        return [query]
    valid = [p.strip() for p in parts if len(p.strip().split()) >= 3]
    return valid if len(valid) > 1 else [query]


# ---------------------------------------------------------------------------
# AIRouter — pure semantic
# ---------------------------------------------------------------------------

class AIRouter:
    def __init__(self, router_config: RouterConfig):
        self.router_config = router_config

    async def route(
        self,
        query: str,
        available_tools: list,
        chat_history: list,
        tool_embeddings: Optional[dict] = None,
        has_user_docs: bool = False,
    ) -> RouterDecision:
        start = time.monotonic()

        tools = [t for t in available_tools if getattr(t, "name", "") not in _SKIP_TOOLS]
        if not tools:
            return RouterDecision(tools=[], reasoning="no tools", latency_ms=0.0)

        # Câu hội thoại → không route
        if _is_chat_query(query):
            return RouterDecision(tools=[], reasoning="chat",
                                  latency_ms=(time.monotonic() - start) * 1000)

        q_lower = query.lower()
        rag_tool = next((t for t in tools if getattr(t, "name", "") == "rag_search"), None)

        # Force-route RAG nếu query rõ ràng hỏi về tài liệu đã upload (mã số sinh viên, bclv)
        _has_doc_code = bool(re.search(r'\b[Bb]\d{7}\b|bclv[_\s]?\w+|\b[A-Z]\d{6,}[_\w]*\b', q_lower))
        if rag_tool and (any(p in q_lower for p in _RAG_FORCE_PATTERNS) or _has_doc_code):
            return RouterDecision(
                tools=[{"name": "rag_search", "parameters": {"query": query}}],
                reasoning="force:rag_search",
                latency_ms=(time.monotonic() - start) * 1000,
            )

        # Follow-up sau rag_search
        if rag_tool and has_user_docs and any(p in q_lower for p in _FOLLOWUP_PATTERNS):
            last_tool = next(
                (m.get("tool") for m in reversed(chat_history)
                 if m.get("role") == "assistant" and m.get("tool")), None
            )
            if last_tool == "rag_search":
                return RouterDecision(
                    tools=[{"name": "rag_search", "parameters": {"query": query}}],
                    reasoning="followup:rag_search",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Pattern pre-filter: phương trình hóa học → force balance_equation
        if _CHEM_EQUATION_PATTERN.search(query):
            chem_tool = next((t for t in tools if getattr(t, "name", "") == "balance_equation"), None)
            if chem_tool:
                logger.info("[AI_ROUTER] chem_pattern matched → balance_equation")
                return RouterDecision(
                    tools=[{"name": "balance_equation", "parameters": {"query": query}}],
                    reasoning="pattern:chem_equation",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Pattern pre-filter: tra cứu nguyên tố → force lookup_element
        if _ELEMENT_LOOKUP_PATTERN.search(query):
            elem_tool = next((t for t in tools if getattr(t, "name", "") == "lookup_element"), None)
            if elem_tool:
                logger.info("[AI_ROUTER] element_pattern matched → lookup_element")
                return RouterDecision(
                    tools=[{"name": "lookup_element", "parameters": {"query": query}}],
                    reasoning="pattern:element_lookup",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Pattern pre-filter: hằng số vật lý → force constants
        if _PHYSICS_CONST_PATTERN.search(query):
            const_tool = next((t for t in tools if getattr(t, "name", "") == "constants"), None)
            if const_tool:
                logger.info("[AI_ROUTER] physics_const_pattern matched → constants")
                return RouterDecision(
                    tools=[{"name": "constants", "parameters": {"query": query}}],
                    reasoning="pattern:physics_constants",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Pattern pre-filter: định luật Ohm → force ohms_law
        if _OHMS_LAW_PATTERN.search(query):
            ohm_tool = next((t for t in tools if getattr(t, "name", "") == "ohms_law"), None)
            if ohm_tool:
                logger.info("[AI_ROUTER] ohms_law_pattern matched → ohms_law")
                return RouterDecision(
                    tools=[{"name": "ohms_law", "parameters": {"query": query}}],
                    reasoning="pattern:ohms_law",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Pattern pre-filter: wiki_summary
        if _WIKI_SUMMARY_PATTERN.search(query):
            ws_tool = next((t for t in tools if "wiki_summary" in getattr(t, "name", "")), None)
            if ws_tool:
                logger.info("[AI_ROUTER] wiki_summary_pattern matched → %s", ws_tool.name)
                return RouterDecision(
                    tools=[{"name": ws_tool.name, "parameters": {"query": query}}],
                    reasoning="pattern:wiki_summary",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Pattern pre-filter: wiki_search
        if _WIKI_SEARCH_PATTERN.search(query):
            ws_tool = next((t for t in tools if "wiki_search" in getattr(t, "name", "")), None)
            if ws_tool:
                logger.info("[AI_ROUTER] wiki_search_pattern matched → %s", ws_tool.name)
                return RouterDecision(
                    tools=[{"name": ws_tool.name, "parameters": {"query": query}}],
                    reasoning="pattern:wiki_search",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Pattern pre-filter: get_user_info
        if _USER_INFO_PATTERN.search(query):
            user_tool = next((t for t in tools if "get_user_info" in getattr(t, "name", "")), None)
            if user_tool:
                logger.info("[AI_ROUTER] user_info_pattern matched → %s", user_tool.name)
                return RouterDecision(
                    tools=[{"name": user_tool.name, "parameters": {"query": query}}],
                    reasoning="pattern:user_info",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Pattern pre-filter: calc
        if _CALC_PATTERN.search(query):
            calc_tool = next(
                (t for t in tools if re.sub(r'^local-mcp-\d+_', '', getattr(t, "name", "")) == "calc"),
                None,
            )
            if calc_tool:
                logger.info("[AI_ROUTER] calc_pattern matched → %s", calc_tool.name)
                return RouterDecision(
                    tools=[{"name": calc_tool.name, "parameters": {"query": query}}],
                    reasoning="pattern:calc",
                    latency_ms=(time.monotonic() - start) * 1000,
                )

        # Semantic routing
        model = _get_model()
        if model is None:
            logger.warning("[AI_ROUTER] Model not ready, no tool selected")
            return RouterDecision(tools=[], reasoning="model_not_ready",
                                  latency_ms=(time.monotonic() - start) * 1000)

        # Multi-intent: tách sub-queries → semantic route từng phần
        sub_queries = _split_multi_intent(query)
        if len(sub_queries) > 1:
            matched, method = self._route_multi_intent(sub_queries, tools, model, tool_embeddings, has_user_docs)
            if len(matched) >= 2:
                latency_ms = (time.monotonic() - start) * 1000
                logger.info("[AI_ROUTER] method=%s tools=%s latency_ms=%.2f",
                            method, [t["name"] for t in matched], latency_ms)
                return RouterDecision(tools=matched, reasoning=f"{method}: {[t['name'] for t in matched]}",
                                      latency_ms=latency_ms)

        # Single intent semantic
        matched = self._semantic_route(query, tools, model, tool_embeddings, rag_boost=has_user_docs)
        method = "semantic+rag_boost" if has_user_docs else "semantic"

        latency_ms = (time.monotonic() - start) * 1000
        reasoning = f"{method}: {[t['name'] for t in matched]}" if matched else f"{method}: no match"
        logger.info("[AI_ROUTER] method=%s tools=%s latency_ms=%.2f",
                    method, [t["name"] for t in matched], latency_ms)
        return RouterDecision(tools=matched, reasoning=reasoning, latency_ms=latency_ms)

    def _route_multi_intent(self, sub_queries: list[str], tools: list, model,
                             tool_embeddings: Optional[dict], rag_boost: bool) -> tuple[list, str]:
        """Semantic route từng sub-query, gom tool khác nhau."""
        seen_names = set()
        matched = []
        for sq in sub_queries:
            hits = self._semantic_route(sq, tools, model, tool_embeddings, rag_boost=rag_boost)
            for hit in hits:
                if hit["name"] not in seen_names:
                    # Gán sub-query làm parameter để _call_tool_service extract đúng từ
                    matched.append({"name": hit["name"], "parameters": {"query": sq}})
                    seen_names.add(hit["name"])
        return matched, "semantic:multi-intent"

    def _semantic_route(self, query: str, tools: list, model,
                        tool_embeddings: Optional[dict], rag_boost: bool = False) -> list:
        """Embed query → cosine với tool passages → top-1 nếu vượt ngưỡng VÀ có gap đủ lớn."""
        try:
            query_emb = model.encode(f"query: {query}", normalize_embeddings=True)

            scores = []
            for tool in tools:
                name = getattr(tool, "name", "")
                if tool_embeddings and name in tool_embeddings:
                    tool_emb = tool_embeddings[name]
                else:
                    tool_emb = model.encode(
                        f"passage: {self._tool_text(tool)}", normalize_embeddings=True
                    )
                score = _cosine(query_emb, tool_emb)
                if rag_boost and name == "rag_search":
                    score += 0.08
                scores.append((score, name))

            scores.sort(reverse=True)
            logger.info("[AI_ROUTER] top scores: %s", [(f"{s:.3f}", n) for s, n in scores[:5]])

            threshold = self.router_config.semantic_threshold
            gap = self.router_config.semantic_gap

            if not scores or scores[0][0] < threshold:
                return []

            best_score, best_name = scores[0]

            # Kiểm tra gap với top-2
            if len(scores) > 1 and scores[1][0] >= threshold:
                diff = best_score - scores[1][0]
                if diff <= 0.01:
                    # Tie thực sự → trả về cả 2
                    return [
                        {"name": best_name, "parameters": {"query": query}},
                        {"name": scores[1][1], "parameters": {"query": query}},
                    ]
                if diff < gap:
                    # Scores cluster, không đủ tự tin → không chọn tool nào
                    logger.info("[AI_ROUTER] gap=%.3f < semantic_gap=%.3f, no confident match", diff, gap)
                    return []

            return [{"name": best_name, "parameters": {"query": query}}]

        except Exception as e:
            logger.error("[AI_ROUTER] Semantic route error: %s", e)
            return []

    @staticmethod
    def _tool_text(tool) -> str:
        """Tạo passage text để embed — description chi tiết là nguồn chính."""
        parts = []
        desc = getattr(tool, "description", "") or ""
        if desc:
            parts.append(desc)
        # quick_command là ví dụ câu hỏi thực tế — rất quan trọng cho semantic match
        quick = getattr(tool, "quick_command", "") or ""
        if quick:
            parts.append(quick)
        display = getattr(tool, "display_name", "") or ""
        if display:
            parts.append(display)
        return " ".join(parts) or getattr(tool, "name", "")

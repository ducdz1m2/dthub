"""
rag_http_clients.py — HTTP clients cho tools-service và RAG service.
"""

import json
import logging
import os
import re

import requests as _http

logger = logging.getLogger(__name__)

TOOLS_SERVICE_URL = os.environ.get("TOOLS_SERVICE_URL", "http://localhost:8002")
RAG_SERVICE_URL = os.environ.get("RAG_SERVICE_URL", "http://localhost:8001")


def _call_tool_service(tool_name: str, query: str, user_id=None) -> str:
    """Gọi tools-service qua HTTP. Tự động map param 'query' → param đúng theo từng tool."""
    _WORD_PARAM_TOOLS = {"english_define", "japanese_lookup"}
    _TITLE_PARAM_TOOLS = {"wiki_summary"}
    bare = re.sub(r'^local-mcp-[^_]+_', '', tool_name)

    if bare in _WORD_PARAM_TOOLS:
        quoted = re.findall(r'["\']([^"\']+)["\']', query)
        if quoted:
            word = quoted[0].strip()
        else:
            cleaned = re.sub(
                r'\s+(tiếng\s+\w+|nghĩa\s+là\s+gì|là\s+gì|có\s+nghĩa|trong\s+tiếng\s+\w+|'
                r'tiếng\s+anh|tiếng\s+nhật|tiếng\s+việt|in\s+japanese|in\s+english|'
                r'nghĩa\s+là|có\s+nghĩa\s+là|dịch\s+ra|dịch\s+sang|tra\s+từ|'
                r'search|tìm\s+kiếm|tra\s+cứu|lookup|define|meaning|what\s+is).*$',
                '', query, flags=re.IGNORECASE
            ).strip()
            cleaned = re.sub(r'^(từ\s+|word\s+|từ\s+điển\s+)', '', cleaned, flags=re.IGNORECASE).strip()
            word = cleaned if cleaned else query.strip()
        parameters = {"word": word}

    elif bare in _TITLE_PARAM_TOOLS:
        quoted = re.findall(r'["\']([^"\']+)["\']', query)
        title = quoted[0] if quoted else query.strip()
        parameters = {"title": title}

    else:
        _SEARCH_PREFIXES = re.compile(
            r'^(tìm kiếm thông tin về|tìm kiếm|search for|search|tra cứu|hỏi về|thông tin về)\s+',
            re.IGNORECASE
        )
        _QUESTION_SUFFIXES = re.compile(
            r'\s+(là ai|là gì|là người như thế nào|như thế nào|ra sao|có phải|không\??)$',
            re.IGNORECASE
        )
        cleaned_query = _SEARCH_PREFIXES.sub('', query).strip()
        cleaned_query = _QUESTION_SUFFIXES.sub('', cleaned_query).strip()
        quoted = re.findall(r'["\']([^"\']+)["\']', cleaned_query)
        parameters = {"query": quoted[0] if quoted else cleaned_query}

    if user_id:
        parameters["user_id"] = user_id

    try:
        resp = _http.post(
            f"{TOOLS_SERVICE_URL}/execute",
            json={"tool": bare, "parameters": parameters},
            timeout=8,
        )
        resp.raise_for_status()
        result = resp.json().get("result", {})
        return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False)
    except _http.exceptions.ConnectionError:
        return "Tools service chưa khởi động (kết nối thất bại)."
    except Exception as e:
        return f"Lỗi gọi tool '{tool_name}': {str(e)}"


def _tools_service_available() -> bool:
    try:
        return _http.get(f"{TOOLS_SERVICE_URL}/health", timeout=2).status_code == 200
    except Exception:
        return False


def _fetch_tools_from_service() -> list[dict]:
    try:
        resp = _http.get(f"{TOOLS_SERVICE_URL}/metadata", timeout=3)
        resp.raise_for_status()
        return resp.json().get("tools", [])
    except Exception:
        return []


def _rag_search(query: str, k: int = 5, namespace: str = "global") -> str:
    try:
        resp = _http.post(
            f"{RAG_SERVICE_URL}/search",
            json={"query": query, "k": k, "namespace": namespace, "min_score": 0.25},
            timeout=5,
        )
        resp.raise_for_status()
        results = resp.json().get("results", [])
        if not results:
            return f"Không tìm thấy thông tin liên quan đến '{query}' trong tài liệu."

        results = sorted(results, key=lambda r: r.get("similarity_score", 0), reverse=True)

        seen_content = set()
        deduped = []
        for r in results:
            fingerprint = r.get("content", "").strip()[:120]
            if fingerprint not in seen_content:
                seen_content.add(fingerprint)
                deduped.append(r)
            if len(deduped) == 3:
                break

        parts = []
        for r in deduped:
            score = r.get("similarity_score", 0)
            source = r.get("source", "")
            page = r.get("page")
            meta = f"[nguồn: {source}" + (f", trang {page}" if page else "") + f", score: {score:.2f}]"
            parts.append(f"{meta}\n{r['content'][:500]}")
        return "\n\n".join(parts)
    except _http.exceptions.ConnectionError:
        return "RAG service chưa khởi động."
    except Exception as e:
        return f"Lỗi tìm kiếm: {str(e)}"


def _rag_available() -> bool:
    try:
        return _http.get(f"{RAG_SERVICE_URL}/health", timeout=2).status_code == 200
    except Exception:
        return False


def _fetch_rag_namespace_summary(namespace: str) -> dict:
    try:
        resp = _http.get(f"{RAG_SERVICE_URL}/namespace/{namespace}/summary", timeout=5)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return {"filenames": [], "sample_texts": []}


def _expand_rag_query(query: str, chat_history: list, max_prev: int = 2) -> str:
    """Expand query ngắn/follow-up bằng context từ history."""
    if not chat_history or len(query.strip()) > 60:
        return query

    prev_queries = [
        m["content"].strip() for m in chat_history
        if m.get("role") == "user" and m.get("content", "").strip()
    ]
    if not prev_queries:
        return query

    anchor = prev_queries[0]
    last_q = prev_queries[-1]

    _STOPWORDS = {"của", "về", "là", "gì", "cái", "nào", "thế", "như", "có", "và",
                  "trong", "trên", "dưới", "với", "cho", "từ", "đến", "này", "đó",
                  "the", "what", "how", "who", "when", "where", "why"}
    query_words = set(query.lower().split())
    anchor_words = set(anchor.lower().split())
    new_content_words = {w for w in query_words if len(w) >= 4 and w not in _STOPWORDS and w not in anchor_words}
    if new_content_words:
        return query

    if anchor.lower() in query.lower() or query.lower() in anchor.lower():
        return query

    if anchor != last_q and last_q.lower() not in query.lower():
        expanded = f"{anchor} — {last_q} — {query}"
    else:
        expanded = f"{anchor} — {query}"

    logger.debug("[RAG_EXPAND] '%s' → '%s'", query, expanded)
    return expanded

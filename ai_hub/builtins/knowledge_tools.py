from typing import Any, Dict, List

import requests

from .registry import BuiltinSpec, register


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "wiki_search",
            "description": "Tìm bài viết Wikipedia theo từ khóa.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "lang": {"type": "string", "description": "vi/en/ja/... (mặc định vi)"},
                    "limit": {"type": "integer", "description": "Số kết quả (mặc định 5)"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "wiki_summary",
            "description": "Lấy tóm tắt Wikipedia theo tiêu đề trang.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "lang": {"type": "string", "description": "vi/en/ja/... (mặc định vi)"},
                },
                "required": ["title"],
            },
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "knowledge://wikipedia",
            "name": "Wikipedia",
            "description": "Tra cứu kiến thức qua Wikipedia API (yêu cầu có Internet).",
            "mimeType": "text/plain",
        }
    ]


def _wiki_base(lang: str) -> str:
    lang = (lang or "").strip().lower() or "vi"
    if not lang.isalpha() or len(lang) > 12:
        lang = "vi"
    return f"https://{lang}.wikipedia.org"


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "wiki_search":
        query = (args.get("query") or "").strip()
        if not query:
            raise ValueError("query is required")
        lang = (args.get("lang") or "").strip() or "vi"
        limit = args.get("limit")
        try:
            limit_n = int(limit) if limit is not None else 5
        except Exception:
            limit_n = 5
        limit_n = max(1, min(20, limit_n))

        base = _wiki_base(lang)
        url = f"{base}/w/api.php"
        r = requests.get(
            url,
            params={
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "utf8": 1,
                "srlimit": limit_n,
            },
            timeout=7,
        )
        r.raise_for_status()
        data = r.json() or {}
        results = []
        for item in (data.get("query") or {}).get("search") or []:
            title = item.get("title")
            pageid = item.get("pageid")
            if title:
                results.append(
                    {
                        "title": title,
                        "pageid": pageid,
                        "url": f"{base}/wiki/{title.replace(' ', '_')}",
                    }
                )
        return {"query": query, "lang": lang, "results": results}

    if tool_name == "wiki_summary":
        title = (args.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")
        lang = (args.get("lang") or "").strip() or "vi"
        base = _wiki_base(lang)
        url = f"{base}/api/rest_v1/page/summary/{title.replace(' ', '_')}"
        r = requests.get(url, timeout=7, headers={"Accept": "application/json"})
        if r.status_code == 404:
            return {"title": title, "lang": lang, "found": False}
        r.raise_for_status()
        data = r.json() or {}
        extract = data.get("extract") or ""
        page = (data.get("content_urls") or {}).get("desktop", {}).get("page")
        return {
            "title": data.get("title") or title,
            "lang": lang,
            "found": True,
            "summary": extract,
            "url": page,
        }

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="knowledge",
        label="MCP tích hợp: Tra cứu kiến thức (Wikipedia)",
        name="knowledge-mcp (builtin)",
        version="0.1",
        description="Tra cứu kiến thức tổng quát qua Wikipedia (yêu cầu Internet).",
        tools=tools,
        resources=resources,
        call=call,
    )
)


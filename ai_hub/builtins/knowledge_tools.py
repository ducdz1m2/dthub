from typing import Any, Dict, List

import requests

from .registry import BuiltinSpec, register


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "wiki_search",
            "description": "Tìm kiếm và tra cứu thông tin về nhân vật, sự kiện lịch sử, khái niệm khoa học, địa danh, tổ chức qua Wikipedia.",
            "keywords": [
                "là ai", "là gì", "là người", "là nhà", "là tổ chức",
                "nhân vật", "người nổi tiếng", "nhà khoa học", "nhà phát minh",
                "lịch sử", "sự kiện", "chiến tranh", "cách mạng",
                "khoa học", "phát minh", "khám phá", "lý thuyết",
                "địa danh", "quốc gia", "thành phố", "châu lục",
                "wikipedia", "wiki", "tìm kiếm", "tra cứu",
                "cho tôi biết về", "giới thiệu về", "thông tin về",
            ],
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
            "description": "Lấy tóm tắt chi tiết về một chủ đề, nhân vật, sự kiện từ Wikipedia.",
            "keywords": [
                "tóm tắt", "tóm lược", "mô tả", "giới thiệu",
                "wiki summary", "wikipedia", "nội dung về", "thông tin về",
            ],
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


_WIKI_HEADERS = {
    "User-Agent": "DTHub-Assistant/1.0 (https://github.com/dthub; contact@dthub.io) python-requests/2.x",
    "Accept": "application/json",
}


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
            headers=_WIKI_HEADERS,
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

        if not results:
            return {"query": query, "lang": lang, "results": [], "summary": None}

        # Tự động lấy summary của kết quả đầu tiên
        top_title = results[0]["title"]
        try:
            sum_url = f"{base}/api/rest_v1/page/summary/{top_title.replace(' ', '_')}"
            sr = requests.get(sum_url, timeout=7, headers=_WIKI_HEADERS)
            if sr.status_code == 200:
                sd = sr.json()
                summary = sd.get("extract", "")
                page_url = (sd.get("content_urls") or {}).get("desktop", {}).get("page", results[0]["url"])
                return {
                    "query": query, "lang": lang,
                    "title": top_title, "summary": summary, "url": page_url,
                    "other_results": [r["title"] for r in results[1:3]],
                }
        except Exception:
            pass

        return {"query": query, "lang": lang, "results": results}

    if tool_name == "wiki_summary":
        title = (args.get("title") or "").strip()
        if not title:
            raise ValueError("title is required")
        lang = (args.get("lang") or "").strip() or "vi"
        base = _wiki_base(lang)
        url = f"{base}/api/rest_v1/page/summary/{title.replace(' ', '_')}"
        r = requests.get(url, timeout=7, headers=_WIKI_HEADERS)
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


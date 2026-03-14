from typing import Any, Dict, List

import requests

from .registry import BuiltinSpec, register


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "japanese_lookup",
            "description": "Tra cứu từ/kanji tiếng Nhật (Jisho.org - yêu cầu Internet).",
            "inputSchema": {
                "type": "object",
                "properties": {"keyword": {"type": "string"}},
                "required": ["keyword"],
            },
        }
    ]


def resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "lang://japanese",
            "name": "Japanese tools",
            "description": "Tra cứu tiếng Nhật qua Jisho API (yêu cầu Internet).",
            "mimeType": "text/plain",
        }
    ]


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "japanese_lookup":
        keyword = (args.get("keyword") or "").strip()
        if not keyword:
            raise ValueError("keyword is required")
        r = requests.get(
            "https://jisho.org/api/v1/search/words",
            params={"keyword": keyword},
            timeout=10,
            headers={"Accept": "application/json"},
        )
        r.raise_for_status()
        data = r.json() or {}
        items = []
        for item in (data.get("data") or [])[:5]:
            japanese = (item.get("japanese") or [{}])[0] or {}
            senses = item.get("senses") or []
            glosses = []
            for s in senses[:2]:
                glosses.append(
                    {
                        "english_definitions": s.get("english_definitions") or [],
                        "parts_of_speech": s.get("parts_of_speech") or [],
                    }
                )
            items.append(
                {
                    "word": japanese.get("word"),
                    "reading": japanese.get("reading"),
                    "is_common": item.get("is_common"),
                    "jlpt": item.get("jlpt") or [],
                    "senses": glosses,
                }
            )
        return {"keyword": keyword, "results": items}

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="japanese",
        label="MCP tích hợp: Nhật bản (tra cứu Jisho)",
        name="japanese-mcp (builtin)",
        version="0.1",
        description="Tra cứu tiếng Nhật qua Jisho.org (yêu cầu Internet).",
        tools=tools,
        resources=resources,
        call=call,
    )
)


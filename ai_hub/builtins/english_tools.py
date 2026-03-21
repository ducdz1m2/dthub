"""english_tools.py — chỉ giữ english_define, bỏ translate."""
from typing import Any, Dict, List

import requests

from .registry import BuiltinSpec, register


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "english_define",
            "description": "Tra nghĩa từ tiếng Anh: định nghĩa, phiên âm, ví dụ (dictionaryapi.dev).",
            "keywords": [
                "tiếng anh", "english", "nghĩa là gì", "định nghĩa", "define",
                "từ điển anh", "phiên âm", "pronunciation", "meaning",
            ],
            "inputSchema": {
                "type": "object",
                "properties": {"word": {"type": "string"}},
                "required": ["word"],
            },
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return []


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "english_define":
        word = (args.get("word") or "").strip()
        if not word:
            raise ValueError("word is required")
        r = requests.get(
            f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}",
            timeout=7, headers={"Accept": "application/json"},
        )
        if r.status_code == 404:
            return {"word": word, "found": False, "entries": []}
        r.raise_for_status()
        data = r.json() or []
        entries = []
        for entry in data[:3]:
            meanings = []
            for m in (entry.get("meanings") or []):
                defs = [{"definition": d.get("definition"), "example": d.get("example")}
                        for d in (m.get("definitions") or [])[:3]]
                meanings.append({"partOfSpeech": m.get("partOfSpeech"), "definitions": defs})
            entries.append({"word": entry.get("word"), "phonetic": entry.get("phonetic"), "meanings": meanings})
        return {"word": word, "found": True, "entries": entries}

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="english",
        label="MCP tích hợp: Từ điển Anh",
        name="english-mcp (builtin)",
        version="0.2",
        description="Tra nghĩa từ tiếng Anh (yêu cầu Internet).",
        tools=tools,
        resources=resources,
        call=call,
    )
)

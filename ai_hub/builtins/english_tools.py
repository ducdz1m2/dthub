from typing import Any, Dict, List

import requests

from .registry import BuiltinSpec, register


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "english_define",
            "description": "Tra nghĩa tiếng Anh (dictionaryapi.dev).",
            "inputSchema": {
                "type": "object",
                "properties": {"word": {"type": "string"}},
                "required": ["word"],
            },
        },
        {
            "name": "translate",
            "description": "Dịch văn bản (MyMemory - miễn phí, yêu cầu Internet).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "from_lang": {"type": "string", "description": "VD: en"},
                    "to_lang": {"type": "string", "description": "VD: vi"},
                },
                "required": ["text", "from_lang", "to_lang"],
            },
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "lang://english",
            "name": "English tools",
            "description": "Tra nghĩa và dịch (yêu cầu Internet).",
            "mimeType": "text/plain",
        }
    ]


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "english_define":
        word = (args.get("word") or "").strip()
        if not word:
            raise ValueError("word is required")
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
        r = requests.get(url, timeout=7, headers={"Accept": "application/json"})
        if r.status_code == 404:
            return {"word": word, "found": False, "entries": []}
        r.raise_for_status()
        data = r.json() or []
        entries = []
        for entry in data[:3]:
            meanings = []
            for m in entry.get("meanings") or []:
                defs = []
                for d in (m.get("definitions") or [])[:3]:
                    defs.append(
                        {
                            "definition": d.get("definition"),
                            "example": d.get("example"),
                        }
                    )
                meanings.append({"partOfSpeech": m.get("partOfSpeech"), "definitions": defs})
            entries.append(
                {
                    "word": entry.get("word"),
                    "phonetic": entry.get("phonetic"),
                    "meanings": meanings,
                }
            )
        return {"word": word, "found": True, "entries": entries}

    if tool_name == "translate":
        text = args.get("text")
        from_lang = (args.get("from_lang") or "").strip().lower()
        to_lang = (args.get("to_lang") or "").strip().lower()
        if text is None or str(text).strip() == "":
            raise ValueError("text is required")
        if not from_lang or not to_lang:
            raise ValueError("from_lang and to_lang are required")
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": str(text), "langpair": f"{from_lang}|{to_lang}"},
            timeout=10,
        )
        r.raise_for_status()
        data = r.json() or {}
        translated = (data.get("responseData") or {}).get("translatedText")
        return {"from": from_lang, "to": to_lang, "text": str(text), "translated": translated}

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="english",
        label="MCP tích hợp: Anh văn (từ điển, dịch)",
        name="english-mcp (builtin)",
        version="0.1",
        description="Tra nghĩa tiếng Anh và dịch văn bản (yêu cầu Internet).",
        tools=tools,
        resources=resources,
        call=call,
    )
)


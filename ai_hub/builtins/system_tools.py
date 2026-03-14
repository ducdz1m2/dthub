import base64
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None

from .registry import BuiltinSpec, register


def _now(tz_name: str | None = None) -> datetime:
    if tz_name and ZoneInfo:
        return datetime.now(ZoneInfo(tz_name))
    return datetime.now(timezone.utc).astimezone()


def tools() -> List[Dict[str, Any]]:
    return [
        {
            "name": "time_now",
            "description": "Lấy thời gian hiện tại theo timezone (mặc định theo hệ thống).",
            "inputSchema": {
                "type": "object",
                "properties": {"tz": {"type": "string", "description": "VD: Asia/Ho_Chi_Minh"}},
            },
        },
        {
            "name": "unix_time",
            "description": "Lấy UNIX timestamp hiện tại (giây).",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "uuid4",
            "description": "Tạo UUID v4.",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "hash_text",
            "description": "Băm chuỗi bằng SHA-256.",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        {
            "name": "base64_encode",
            "description": "Mã hóa chuỗi sang Base64 (UTF-8).",
            "inputSchema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
        },
        {
            "name": "base64_decode",
            "description": "Giải mã Base64 sang chuỗi (UTF-8).",
            "inputSchema": {
                "type": "object",
                "properties": {"b64": {"type": "string"}},
                "required": ["b64"],
            },
        },
    ]


def resources() -> List[Dict[str, Any]]:
    return [
        {
            "uri": "system://timezones",
            "name": "Timezones",
            "description": "Timezone theo chuẩn IANA (nếu môi trường hỗ trợ zoneinfo).",
            "mimeType": "text/plain",
        }
    ]


def call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    args = arguments or {}

    if tool_name == "time_now":
        tz = (args.get("tz") or "").strip() or None
        now = _now(tz)
        return {
            "iso": now.isoformat(),
            "timezone": str(now.tzinfo),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S"),
        }

    if tool_name == "unix_time":
        ts = int(datetime.now(timezone.utc).timestamp())
        return {"timestamp": ts}

    if tool_name == "uuid4":
        return {"uuid": str(uuid.uuid4())}

    if tool_name == "hash_text":
        text = args.get("text")
        if text is None:
            raise ValueError("text is required")
        data = str(text).encode("utf-8")
        return {"sha256": hashlib.sha256(data).hexdigest()}

    if tool_name == "base64_encode":
        text = args.get("text")
        if text is None:
            raise ValueError("text is required")
        data = str(text).encode("utf-8")
        return {"base64": base64.b64encode(data).decode("ascii")}

    if tool_name == "base64_decode":
        b64 = args.get("b64")
        if b64 is None:
            raise ValueError("b64 is required")
        data = base64.b64decode(str(b64).encode("ascii"), validate=True)
        return {"text": data.decode("utf-8")}

    raise ValueError(f"unknown tool: {tool_name}")


register(
    BuiltinSpec(
        kind="system",
        label="MCP tích hợp: Hệ thống (thời gian, hash, UUID...)",
        name="system-mcp (builtin)",
        version="0.1",
        description="Các tiện ích hệ thống chạy trực tiếp trong DTHub.",
        tools=tools,
        resources=resources,
        call=call,
    )
)


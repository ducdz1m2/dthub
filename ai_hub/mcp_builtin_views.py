import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .builtin_mcp import get_builtin_definition
from .models import MCPServer as MCPServerModel


def _has_access(request, device_id: str) -> bool:
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        try:
            obj = MCPServerModel.objects.filter(device_id=device_id, is_active=True).only(
                "is_public", "owner_id"
            ).first()
            if not obj:
                return False
            if obj.is_public:
                return True
            return bool(obj.owner_id) and obj.owner_id == user.id
        except Exception:
            return False
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        return False
    token = auth.removeprefix("Bearer ").strip()
    if not token:
        return False
    try:
        return MCPServerModel.objects.filter(device_id=device_id, auth_token=token, is_active=True).exists()
    except Exception:
        return False


def _ensure_server(device_id: str) -> bool:
    try:
        return MCPServerModel.objects.filter(device_id=device_id, is_active=True).exists()
    except Exception:
        return False


@require_http_methods(["GET"])
def builtin_info(request, kind: str, device_id: str):
    if not _ensure_server(device_id):
        return JsonResponse({"error": "not found"}, status=404)
    if not _has_access(request, device_id):
        return JsonResponse({"error": "unauthorized"}, status=401)
    definition = get_builtin_definition(kind)
    return JsonResponse({"name": definition["name"], "status": "ok"})


@require_http_methods(["GET"])
def builtin_mcp_info(request, kind: str, device_id: str):
    if not _ensure_server(device_id):
        return JsonResponse({"error": "not found"}, status=404)
    if not _has_access(request, device_id):
        return JsonResponse({"error": "unauthorized"}, status=401)
    definition = get_builtin_definition(kind)
    return JsonResponse(
        {
            "name": definition["name"],
            "version": definition["version"],
            "description": definition["description"],
        }
    )


@require_http_methods(["GET"])
def builtin_mcp_tools(request, kind: str, device_id: str):
    if not _ensure_server(device_id):
        return JsonResponse({"error": "not found"}, status=404)
    if not _has_access(request, device_id):
        return JsonResponse({"error": "unauthorized"}, status=401)
    definition = get_builtin_definition(kind)
    return JsonResponse({"tools": definition["tools"]()})


@require_http_methods(["GET"])
def builtin_mcp_resources(request, kind: str, device_id: str):
    if not _ensure_server(device_id):
        return JsonResponse({"error": "not found"}, status=404)
    if not _has_access(request, device_id):
        return JsonResponse({"error": "unauthorized"}, status=401)
    definition = get_builtin_definition(kind)
    return JsonResponse({"resources": definition["resources"]()})


@csrf_exempt
@require_http_methods(["POST"])
def builtin_mcp_call(request, kind: str, device_id: str):
    if not _ensure_server(device_id):
        return JsonResponse({"error": "not found"}, status=404)
    if not _has_access(request, device_id):
        return JsonResponse({"error": "unauthorized"}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except Exception:
        payload = {}
    tool_name = payload.get("name")
    arguments = payload.get("arguments") or {}

    definition = get_builtin_definition(kind)
    try:
        result = definition["call"](tool_name, arguments)
        return JsonResponse({"success": True, "result": result})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

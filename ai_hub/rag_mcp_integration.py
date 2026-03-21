"""
rag_mcp_integration.py — RAGMCPService: pipeline chính AIRouter → Tools → LLM.
"""

import json
import logging
import threading

from asgiref.sync import sync_to_async

from .mcp_tools.llm_processor import LLMProcessor
from .mcp_tools.db_helpers import (
    get_chat_history_async, save_chat_message_async,
    get_chat_history_sync, save_chat_message_sync,
)
from .mcp_tools.ai_router import AIRouter, RouterConfig, RouterDecision
from .mcp_tools.tool_orchestrator import ToolOrchestrator
from .rag_http_clients import (
    _call_tool_service, _tools_service_available, _fetch_tools_from_service,
    _rag_search, _rag_available, _fetch_rag_namespace_summary, _expand_rag_query,
    TOOLS_SERVICE_URL, RAG_SERVICE_URL,
)
from .rag_builtin_handlers import _call_builtin

logger = logging.getLogger(__name__)


class _Dispatcher:
    def __init__(self):
        self.tools: dict = {}


class RAGMCPService:
    """Service chính — WebSocket chat và ESP32 sync API."""

    def __init__(self):
        self.dispatcher = _Dispatcher()
        self.tool_embeddings: dict = {}
        self.llm_processor = LLMProcessor(
            llm_model="qwen2.5:3b",
            temperature=0.1,
            max_tokens=1024,
        )
        if _tools_service_available():
            self._load_tools_from_service()
        else:
            logger.info("[TOOLS] Service offline")

        self._register_builtin_tools()
        self._register_django_api_tools()

        if _rag_available():
            self._register_rag_tool()
        else:
            logger.info("[RAG] Service offline, rag_search không được đăng ký")

        self._reload_llm_config()

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _load_tools_from_service(self):
        tools = _fetch_tools_from_service()
        for tool in tools:
            name = tool.get("name")
            if not name:
                continue
            def make_handler(tool_name):
                def handler(query: str, user_id=None):
                    return _call_tool_service(tool_name, query, user_id=user_id)
                return handler
            self.dispatcher.tools[name] = {
                "handler": make_handler(name),
                "description": tool.get("description", ""),
                "keywords": tool.get("keywords", []),
                "display_name": tool.get("name", "").replace("_", " ").title(),
            }
        logger.info("[TOOLS] Loaded %d tools from tools-service", len(tools))
        self._build_tool_embeddings()

    def _register_rag_tool(self):
        def rag_search_handler(query: str, user_id=None):
            namespace = f"user_{user_id}" if user_id else "global"
            return _rag_search(query, k=5, namespace=namespace)
        self.dispatcher.tools["rag_search"] = {
            "handler": rag_search_handler,
            "description": "Tìm kiếm thông tin trong tài liệu cá nhân đã upload của người dùng.",
            "keywords": ["tài liệu", "luận văn", "báo cáo", "file", "đã upload", "đã tải",
                         "nội dung", "trong tài liệu", "tìm trong", "tìm kiếm tài liệu"],
        }
        logger.info("[RAG] rag_search tool registered")
        self._build_tool_embeddings()

    def _register_kb_tool(self, kb_id: int, kb_name: str, namespace: str,
                          description: str, keywords: list):
        tool_name = f"kb_{namespace}"
        def kb_handler(query: str, user_id=None):
            return _rag_search(query, k=5, namespace=namespace)
        self.dispatcher.tools[tool_name] = {
            "handler": kb_handler,
            "description": description,
            "keywords": keywords,
            "_kb_id": kb_id,
            "_kb_name": kb_name,
            "_namespace": namespace,
        }
        logger.info("[RAG] KB tool registered: %s", tool_name)

    def _sync_kb_tools(self, user_id=None):
        for k in [k for k in list(self.dispatcher.tools) if k.startswith("kb_")]:
            del self.dispatcher.tools[k]
        if not _rag_available():
            return
        try:
            from .models import KnowledgeBase, UserKnowledgeBase
            kbs = list(KnowledgeBase.objects.filter(is_system=True))
            if user_id:
                user_kb_ids = list(UserKnowledgeBase.objects.filter(
                    user_id=user_id, is_active=True
                ).values_list('kb_id', flat=True))
                kbs.extend(KnowledgeBase.objects.filter(id__in=user_kb_ids, is_system=False))
            for kb in kbs:
                summary = _fetch_rag_namespace_summary(kb.namespace)
                filenames = summary.get("filenames", [])
                sample_texts = summary.get("sample_texts", [])
                if not filenames and not sample_texts:
                    continue
                content_hint = " ".join(t.replace("passage: ", "").strip() for t in sample_texts)[:300]
                description = (
                    f"Tìm kiếm thông tin trong kho tri thức '{kb.name}'. Dùng khi hỏi về {kb.name}. "
                    + (f"Nội dung: {content_hint}." if content_hint else "")
                ).strip()
                name_words = kb.name.lower().split()
                keywords = list(dict.fromkeys(
                    [kb.name.lower()] + name_words
                    + ([kb.category.lower()] if kb.category else [])
                    + [f.replace('_', ' ').replace('-', ' ').lower() for f in filenames[:3]]
                ))
                self._register_kb_tool(kb.id, kb.name, kb.namespace, description, keywords)
        except Exception as e:
            logger.warning("[RAG] _sync_kb_tools error: %s", e)
        self._build_tool_embeddings()

    def ensure_rag_tool(self) -> bool:
        if "rag_search" in self.dispatcher.tools:
            return True
        if _rag_available():
            self._register_rag_tool()
            return True
        return False

    def _register_builtin_tools(self):
        from .builtins.registry import list_specs
        for spec in list_specs():
            try:
                tool_defs = spec.tools()
            except Exception:
                continue
            for tool_def in tool_defs:
                name = tool_def.get("name")
                if not name:
                    continue
                def make_handler(spec_call, tname, schema):
                    def handler(query: str, user_id=None):
                        return _call_builtin(spec_call, tname, query, schema)
                    return handler
                schema = tool_def.get("inputSchema", {})
                self.dispatcher.tools[name] = {
                    "handler": make_handler(spec.call, name, schema),
                    "description": tool_def.get("description", ""),
                    "keywords": tool_def.get("keywords", []),
                }
        logger.info("[BUILTIN] Registered %d builtin tools",
                    len([n for n in self.dispatcher.tools if n != "rag_search"]))

    def refresh_rag_tool_description(self, user_id: int):
        if "rag_search" not in self.dispatcher.tools:
            return
        namespace = f"user_{user_id}"
        summary = _fetch_rag_namespace_summary(namespace)
        filenames = summary.get("filenames", [])
        sample_texts = summary.get("sample_texts", [])
        if not filenames and not sample_texts:
            return
        file_part = f"Tài liệu: {', '.join(filenames)}." if filenames else ""
        content_part = f"Nội dung liên quan: {' '.join(sample_texts)[:300]}." if sample_texts else ""
        self.dispatcher.tools["rag_search"]["description"] = " ".join(filter(None, [
            "Tìm kiếm thông tin trong tài liệu đã upload của người dùng.", file_part, content_part
        ]))
        self._build_tool_embeddings()


    def _build_tool_embeddings(self):
        from .mcp_tools.ai_router import _get_model, _SKIP_TOOLS
        model = _get_model()
        if model is None:
            self._schedule_embedding_retry()
            return
        try:
            from ai_hub.models import MCPTool
            import django.db, re as _re
            django.db.close_old_connections()
            _PREFIX = _re.compile(r'^local-mcp-[^_]+_')
            db_extra = {}
            for t in MCPTool.objects.filter(is_enabled=True):
                bare = _PREFIX.sub('', t.name)
                entry = (t.description or "", t.quick_command or "", t.display_name or "")
                db_extra[t.name] = entry
                db_extra[bare] = entry
        except Exception:
            db_extra = {}
        self._do_build_embeddings(model, _SKIP_TOOLS, db_extra)

    def _do_build_embeddings(self, model, skip_tools, db_extra: dict = None):
        try:
            db_extra = db_extra or {}
            new_cache = {}
            for name, cfg in self.dispatcher.tools.items():
                if name in skip_tools:
                    continue
                db_desc, quick, display = db_extra.get(name, ("", "", ""))
                desc = db_desc or cfg.get("description", "") or ""
                text = " ".join(filter(None, [desc, quick, display])).strip()
                if not text:
                    continue
                new_cache[name] = model.encode(f"passage: {text}", normalize_embeddings=True)
            self.tool_embeddings = new_cache
            logger.info("[TOOLS] Built embeddings for %d tools", len(new_cache))
        except Exception as e:
            logger.warning("[TOOLS] Build embeddings failed: %s", e)

    def _schedule_embedding_retry(self):
        try:
            from ai_hub.models import MCPTool
            import django.db, re as _re
            django.db.close_old_connections()
            _PREFIX = _re.compile(r'^local-mcp-[^_]+_')
            db_extra = {}
            for t in MCPTool.objects.filter(is_enabled=True):
                bare = _PREFIX.sub('', t.name)
                entry = (t.description or "", t.quick_command or "", t.display_name or "")
                db_extra[t.name] = entry
                db_extra[bare] = entry
        except Exception:
            db_extra = {}

        def _retry():
            from .mcp_tools.ai_router import _get_model, _SKIP_TOOLS
            import time
            for _ in range(30):
                time.sleep(2)
                model = _get_model()
                if model is not None:
                    self._do_build_embeddings(model, _SKIP_TOOLS, db_extra)
                    return
            logger.warning("[TOOLS] Model không load được sau 60s")
        threading.Thread(target=_retry, daemon=True, name="embedding-retry").start()

    def _register_django_api_tools(self):
        """Đăng ký các Django API tools: orders, products, user info, devices, system, weather."""

        def _get_order_status(query: str, user_id=None) -> str:
            if not user_id:
                return "Bạn cần đăng nhập để xem đơn hàng."
            try:
                from orders.models import Order
                orders = Order.objects.filter(user_id=user_id).select_related("product").order_by("-created_at")[:10]
                if not orders.exists():
                    return "Bạn chưa có đơn hàng nào."
                return "Đơn hàng của bạn:\n" + "\n".join(
                    f"- Đơn #{o.id}: {o.product.name} | {o.get_status_display()} | "
                    f"{o.total:,.0f} VNĐ | {o.created_at.strftime('%d/%m/%Y')}"
                    for o in orders
                )
            except Exception as e:
                return f"Lỗi lấy đơn hàng: {e}"

        def _list_products(query: str, user_id=None) -> str:
            try:
                from products.models import Product
                qs = Product.objects.filter(is_active=True)
                if query.strip():
                    qs = qs.filter(name__icontains=query.strip())
                products = qs.order_by("name")[:20]
                if not products.exists():
                    return f"Không tìm thấy sản phẩm nào."
                return "Sản phẩm hiện có:\n" + "\n".join(
                    f"- {p.name} | {p.get_product_type_display()} | {p.price:,.0f} VNĐ | Còn {p.stock}"
                    for p in products
                )
            except Exception as e:
                return f"Lỗi lấy sản phẩm: {e}"

        def _get_user_info(query: str, user_id=None) -> str:
            if not user_id:
                return "Bạn cần đăng nhập để xem thông tin tài khoản."
            try:
                from django.contrib.auth import get_user_model
                user = get_user_model().objects.filter(pk=user_id).first()
                if not user:
                    return "Không tìm thấy thông tin người dùng."
                profile = getattr(user, "profile", None)
                lines = [
                    f"Tên: {user.get_full_name() or user.username}",
                    f"Email: {user.email}",
                    f"Vai trò: {getattr(user, 'role_display', '')}",
                ]
                if profile:
                    if getattr(profile, "phone", None):
                        lines.append(f"Điện thoại: {profile.phone}")
                    if getattr(profile, "address", None):
                        lines.append(f"Địa chỉ: {profile.address}")
                return "\n".join(lines)
            except Exception as e:
                return f"Lỗi lấy thông tin: {e}"

        def _list_devices(query: str, user_id=None) -> str:
            try:
                from .models import ESP32Device
                from django.utils import timezone as tz
                devices = ESP32Device.objects.filter(is_active=True)
                if not devices.exists():
                    return "Không có thiết bị nào đang hoạt động."
                lines = [
                    f"- {d.name}: {'Online' if d.last_seen and (tz.now() - d.last_seen).total_seconds() < 300 else 'Offline'}"
                    for d in devices
                ]
                return f"Tìm thấy {len(lines)} thiết bị:\n" + "\n".join(lines)
            except Exception as e:
                return f"Lỗi lấy danh sách thiết bị: {e}"

        def _device_control(query: str, user_id=None) -> str:
            try:
                from .models import DeviceControlLabel
                import requests as _req
                q = query.lower()
                labels = DeviceControlLabel.objects.filter(is_active=True).select_related("device")
                target = next((l for l in labels if l.label.lower() in q), None)
                if not target:
                    available = ", ".join(l.label for l in labels)
                    return f"Không tìm thấy thiết bị phù hợp. Nhãn hiện có: {available or 'chưa có'}."
                device = target.device
                if not device.ip_address:
                    return f"Thiết bị '{device.name}' chưa có địa chỉ IP."
                is_on = any(x in q for x in ["bật", "mở", "bat", "mo", "on", "active"])
                is_off = any(x in q for x in ["tắt", "đóng", "tat", "dong", "off", "stop"])
                action = "on" if is_on else ("off" if is_off else None)
                if not action:
                    return f"Hãy nói rõ 'bật' hay 'tắt' cho '{target.label}'."
                resp = _req.post(
                    f"http://{device.ip_address}/control",
                    json={"command": f"{target.channel}_{action}", "parameters": {}},
                    timeout=5,
                )
                status_text = "BẬT" if action == "on" else "TẮT"
                return f"Đã {status_text} '{target.label}' thành công!" if resp.status_code == 200 \
                    else f"Thiết bị trả về lỗi HTTP {resp.status_code}."
            except Exception as e:
                return f"Lỗi điều khiển thiết bị: {e}"

        def _system_info(query: str, user_id=None) -> str:
            try:
                import platform, datetime
                now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                try:
                    import psutil
                    cpu = f"{psutil.cpu_percent(interval=0.5):.1f}%"
                    ram = psutil.virtual_memory()
                    ram_info = f"{ram.percent:.1f}% ({ram.used // 1024**2}MB / {ram.total // 1024**2}MB)"
                except ImportError:
                    cpu, ram_info = "N/A", "N/A"
                return f"Hệ thống DTHub\n- Thời gian: {now}\n- OS: {platform.system()} {platform.release()}\n- CPU: {cpu}\n- RAM: {ram_info}"
            except Exception as e:
                return f"Lỗi lấy thông tin hệ thống: {e}"

        def _weather_info(query: str, user_id=None) -> str:
            try:
                import re as _re
                from .rag_http_clients import _http
                m = _re.search(r'(?:thời tiết|weather|nhiệt độ)\s+(?:ở\s+|tại\s+|của\s+)?([^\s?]+)', query, _re.IGNORECASE)
                city = m.group(1) if m else "Hanoi"
                resp = _http.get(f"https://wttr.in/{city}?format=3&lang=vi", timeout=5, headers={"User-Agent": "curl/7.0"})
                return resp.text.strip() if resp.status_code == 200 else f"Không lấy được thời tiết cho '{city}'."
            except Exception as e:
                return f"Lỗi lấy thời tiết: {e}"

        self.dispatcher.tools.update({
            "get_order_status": {"handler": _get_order_status, "description": "Xem đơn hàng của người dùng.", "keywords": ["đơn hàng", "order", "trạng thái đơn", "đặt hàng", "mua hàng"]},
            "list_products": {"handler": _list_products, "description": "Liệt kê sản phẩm trên sàn DTHub.", "keywords": ["sản phẩm", "product", "hàng hóa", "mua gì", "bán gì", "giá"]},
            "get_user_info": {"handler": _get_user_info, "description": "Lấy thông tin tài khoản người dùng.", "keywords": ["tài khoản", "thông tin cá nhân", "profile", "user info"]},
            "list_devices": {"handler": _list_devices, "description": "Liệt kê thiết bị IoT đang online/offline.", "keywords": ["danh sách thiết bị", "thiết bị nào", "online", "offline", "list devices"]},
            "device_control": {"handler": _device_control, "description": "Điều khiển thiết bị IoT: bật/tắt đèn, quạt, relay.", "keywords": ["bật", "tắt", "điều khiển", "thiết bị", "relay", "đèn", "quạt"]},
            "system_info": {"handler": _system_info, "description": "Thông tin hệ thống: thời gian, OS, CPU, RAM.", "keywords": ["hệ thống", "system", "cpu", "ram", "thông tin máy", "server"]},
            "weather_info": {"handler": _weather_info, "description": "Thông tin thời tiết theo thành phố.", "keywords": ["thời tiết", "weather", "nhiệt độ", "mưa", "nắng", "dự báo"]},
        })
        logger.info("[DJANGO_API] Registered 7 Django API tools")

    def _reload_llm_config(self):
        try:
            from .models import AIConfiguration
            config = AIConfiguration.objects.select_related('llm_config').filter(
                user__isnull=True, is_default=True, is_active=True
            ).first()
            if config and config.llm_config:
                lc = config.llm_config
                self.llm_processor.llm_model = lc.model
                self.llm_processor.temperature = lc.temperature
                self.llm_processor.max_tokens = lc.max_tokens
                self.llm_processor.response_language = lc.response_language
        except Exception:
            pass


    # ------------------------------------------------------------------
    # Permission check
    # ------------------------------------------------------------------

    async def _check_user_tool_access(self, user_id, tool_name: str):
        if tool_name.startswith("kb_") or tool_name == "rag_search":
            if not user_id:
                return False, "403: Bạn cần đăng nhập để dùng công cụ này."
            return True, None
        if not user_id:
            return False, f"403: Bạn cần đăng nhập để dùng công cụ '{tool_name}'."

        @sync_to_async
        def _check():
            from .models import MCPTool, UserMCPTool
            tool = MCPTool.objects.filter(name=tool_name, is_enabled=True).first() \
                or MCPTool.objects.filter(name__endswith=f"_{tool_name}", is_enabled=True).first()
            if not tool:
                return False, f"403: Công cụ '{tool_name}' chưa được đăng ký trong hệ thống."
            if tool.is_system:
                if tool.source_server and not tool.source_server.is_active:
                    return False, f"403: Server của công cụ '{tool_name}' đang bị tắt."
                return True, None
            if tool.source_server and tool.source_server.owner_id == user_id:
                if not tool.source_server.is_active:
                    return False, f"403: Server của công cụ '{tool_name}' đang bị tắt."
                return True, None
            if tool.source_server and not tool.source_server.is_active:
                return False, f"403: Server của công cụ '{tool_name}' đang bị tắt."
            has = UserMCPTool.objects.filter(user_id=user_id, tool=tool, is_active=True).exists()
            if not has:
                return False, f"403: Công cụ '{tool.display_name or tool_name}' chưa được thêm vào bộ sưu tập của bạn."
            return True, None

        try:
            return await _check()
        except Exception as e:
            return False, f"500: Lỗi kiểm tra quyền: {str(e)}"

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    async def _get_llm_config(self, user_id):
        from .models import AIConfiguration

        @sync_to_async
        def _fetch():
            qs = AIConfiguration.objects.select_related('llm_config')
            cfg = qs.filter(user_id=user_id, is_default=True, is_active=True).first() if user_id else None
            if not cfg:
                cfg = qs.filter(user__isnull=True, is_default=True, is_active=True).first()
            return cfg.llm_config if cfg else None

        try:
            return await _fetch()
        except Exception:
            return None

    async def _user_has_documents(self, user_id) -> bool:
        if not user_id:
            return False
        @sync_to_async
        def _check():
            from .models import UserDocument
            return UserDocument.objects.filter(user_id=user_id, status='success').exists()
        try:
            return await _check()
        except Exception:
            return False

    async def _get_user_tools(self, user_id):
        if not self.dispatcher.tools and _tools_service_available():
            self._load_tools_from_service()
        if "rag_search" not in self.dispatcher.tools and _rag_available():
            self._register_rag_tool()
        if _rag_available():
            await sync_to_async(self._sync_kb_tools)(user_id)
            if user_id:
                threading.Thread(
                    target=self.refresh_rag_tool_description, args=(user_id,),
                    daemon=True, name=f"rag-desc-refresh-{user_id}"
                ).start()

        allowed_names, db_keywords = await self._get_allowed_tool_names_with_keywords(user_id)

        class _ToolObj:
            def __init__(self, name, description, keywords, allowed):
                self.name = name
                self.description = description
                self.keywords = keywords
                self.is_system = False
                self.is_enabled = True
                self.allowed = allowed

        tools = []
        for name, cfg in self.dispatcher.tools.items():
            merged_kws = list(dict.fromkeys((cfg.get("keywords") or []) + (db_keywords.get(name) or [])))
            tools.append(_ToolObj(
                name=name,
                description=cfg.get("description", ""),
                keywords=merged_kws,
                allowed=name.startswith("kb_") or (name in allowed_names),
            ))
        return tools

    async def _get_allowed_tool_names_with_keywords(self, user_id) -> tuple[set, dict]:
        @sync_to_async
        def _fetch():
            import re
            from .models import MCPTool, UserMCPTool
            _PREFIX = re.compile(r'^local-mcp-[^_]+_')

            def _both(names):
                result = set(names)
                for n in names:
                    result.add(_PREFIX.sub('', n))
                return result

            system_qs = MCPTool.objects.filter(is_system=True, is_enabled=True)
            system_names = _both(system_qs.values_list('name', flat=True))
            db_kw = {}
            for t in system_qs:
                bare = _PREFIX.sub('', t.name)
                kws = t.keywords or []
                db_kw[t.name] = kws
                db_kw[bare] = kws

            if not user_id:
                return system_names, db_kw

            user_qs = MCPTool.objects.filter(
                user_assignments__user_id=user_id, user_assignments__is_active=True, is_enabled=True,
            ).exclude(source_server__isnull=False, source_server__is_active=False)
            user_names = _both(user_qs.values_list('name', flat=True))
            for t in user_qs:
                bare = _PREFIX.sub('', t.name)
                db_kw[t.name] = t.keywords or []
                db_kw[bare] = t.keywords or []

            private_qs = MCPTool.objects.filter(
                source_server__owner_id=user_id, is_enabled=True, source_server__is_active=True,
            )
            private_names = _both(private_qs.values_list('name', flat=True))
            for t in private_qs:
                bare = _PREFIX.sub('', t.name)
                db_kw[t.name] = t.keywords or []
                db_kw[bare] = t.keywords or []

            return system_names | user_names | private_names, db_kw

        try:
            return await _fetch()
        except Exception as e:
            logger.warning("[TOOLS] _get_allowed_tool_names_with_keywords error: %s", e)
            return set(self.dispatcher.tools.keys()), {}


    # ------------------------------------------------------------------
    # Main WebSocket pipeline
    # ------------------------------------------------------------------

    async def process_websocket_query(self, consumer, query: str, session_id: str = None):
        import time
        self.ensure_rag_tool()
        start = time.monotonic()

        scope_user = getattr(consumer, "scope", {}).get("user") if consumer else None
        user_id = scope_user.id if scope_user and getattr(scope_user, "is_authenticated", False) else None

        llm_config = await self._get_llm_config(user_id)
        if llm_config:
            self.llm_processor.llm_model = llm_config.model
            self.llm_processor.temperature = llm_config.temperature
            self.llm_processor.max_tokens = llm_config.max_tokens
            self.llm_processor.response_language = llm_config.response_language

        if hasattr(consumer, 'send'):
            await consumer.send(text_data=json.dumps({"type": "thinking", "done": False}, ensure_ascii=False))

        available_tools = await self._get_user_tools(user_id)
        chat_history = await get_chat_history_async(session_id or "default", limit=10, user_id=user_id)
        has_user_docs = await self._user_has_documents(user_id)

        router_cfg = RouterConfig.from_llm_config(llm_config) if llm_config else RouterConfig()
        router = AIRouter(router_cfg)
        try:
            decision = await router.route(query, available_tools, chat_history, self.tool_embeddings, has_user_docs=has_user_docs)
        except Exception as e:
            logger.warning("[ROUTER_FALLBACK] %s", e)
            decision = RouterDecision(tools=[], reasoning="fallback", latency_ms=0.0)

        _SKIP = {"general_chat", "help_info", "no_tool_available"}
        real_tools = [t for t in decision.tools if t["name"] not in _SKIP]
        tool_results = []
        denied_msg = None

        # Nếu router không chọn tool → kiểm tra DB bằng keyword
        if not real_tools and decision.reasoning not in ("chat",):
            @sync_to_async
            def _find_candidate():
                from .models import MCPTool
                q = query.lower()
                best, best_hits = None, 0
                for t in MCPTool.objects.filter(is_enabled=True).exclude(name__in=list(_SKIP)):
                    hits = sum(1 for kw in (t.keywords or []) if kw and kw.lower() in q)
                    if hits > best_hits:
                        best_hits, best = hits, t
                return best if best_hits >= 1 else None

            candidate = await _find_candidate()
            if candidate:
                @sync_to_async
                def _user_has_tool(tname):
                    from .models import MCPTool, UserMCPTool
                    t = MCPTool.objects.filter(name=tname).first()
                    if not t:
                        return None, False, False
                    server_active = (not t.source_server) or t.source_server.is_active
                    if t.is_system:
                        return t, True, server_active
                    has = UserMCPTool.objects.filter(user_id=user_id, tool=t, is_active=True).exists() if user_id else False
                    return t, has, server_active

                tool_obj, user_has, server_active = await _user_has_tool(candidate.name)
                if tool_obj:
                    dname = tool_obj.display_name or tool_obj.name
                    if not server_active:
                        denied_msg = f"⚠️ Công cụ **{dname}** có thể xử lý yêu cầu này nhưng server đang bị tắt."
                    elif not user_has:
                        denied_msg = f"⚠️ Yêu cầu này cần công cụ **{dname}** nhưng bạn chưa bật nó.\n\n👉 Vào [Trung tâm công cụ](/ai/tools/) để thêm **{dname}**."

        if real_tools:
            allowed_set = {t.name for t in available_tools if getattr(t, "allowed", True)}
            not_allowed = [
                t for t in real_tools
                if t["name"] not in allowed_set
                and not t["name"].startswith("kb_")
                and t["name"] != "rag_search"
            ]
            if not_allowed:
                tool_name = not_allowed[0]["name"]
                @sync_to_async
                def _get_display(tname):
                    from .models import MCPTool
                    import re as _re
                    t = MCPTool.objects.filter(name=tname, is_enabled=True).first() \
                        or MCPTool.objects.filter(name__endswith=f"_{tname}", is_enabled=True).first()
                    return t.display_name if t else tname
                display = await _get_display(tool_name)
                denied_msg = f"Công cụ '{display}' chưa được bật. Vào Trung tâm công cụ để thêm nó."
            else:
                orchestrator = ToolOrchestrator(
                    dispatcher=self.dispatcher,
                    check_access_fn=self._check_user_tool_access,
                )
                expanded_tools = []
                for t in real_tools:
                    if t["name"] == "rag_search" or t["name"].startswith("kb_"):
                        expanded_q = _expand_rag_query(t.get("parameters", {}).get("query", query), chat_history)
                        expanded_tools.append({**t, "parameters": {**t.get("parameters", {}), "query": expanded_q}})
                    else:
                        expanded_tools.append(t)
                raw_results = await orchestrator.execute(
                    RouterDecision(tools=expanded_tools, reasoning=decision.reasoning, latency_ms=decision.latency_ms),
                    query, user_id
                )
                for r in raw_results:
                    if r.success:
                        tool_results.append({"tool": r.tool_name, "result": r.result})
                    elif r.error and r.error.startswith("403:"):
                        denied_msg = r.error
                        break
                    elif r.error and not r.error.startswith("timeout"):
                        tool_results.append({"tool": r.tool_name, "result": r.error})

        if denied_msg:
            raw = denied_msg.replace("403: ", "").replace("403:", "").strip()
            if raw.startswith("⚠️") or "đang bị tắt" in raw:
                final_response = raw if raw.startswith("⚠️") else f"⚠️ {raw}"
            else:
                final_response = f"⚠️ {raw}\n\n👉 Vào [Trung tâm công cụ](/ai/tools/) để thêm công cụ này."
        else:
            tool_results = [
                r for r in tool_results
                if r.get("result") and not (
                    r.get("tool") == "rag_search" and "Không tìm thấy" in str(r.get("result", ""))
                )
            ]
            no_tool_disclaimer = not real_tools and not tool_results and decision.reasoning not in ("chat",)
            final_response = await self.llm_processor.synthesize_response(
                query, tool_results, self.llm_processor.response_language, chat_history,
                no_tool_hint=no_tool_disclaimer,
            )

        elapsed = time.monotonic() - start
        tool_used_names = [t["name"] for t in real_tools] if real_tools else ["general"]
        tool_used_str = tool_used_names[0] if len(tool_used_names) == 1 else "+".join(tool_used_names)

        if hasattr(consumer, 'send'):
            await consumer.send(text_data=json.dumps(
                {"type": "chunk", "chunk": final_response, "done": False}, ensure_ascii=False
            ))
            await consumer.send(text_data=json.dumps(
                {"type": "response", "done": True, "full_response": final_response,
                 "tool_used": tool_used_str, "response_time": round(elapsed, 2)},
                ensure_ascii=False,
            ))

        await save_chat_message_async(
            session_id or "default", query, final_response, tool_used_str, elapsed, user_id=user_id,
        )
        return final_response

    # ------------------------------------------------------------------
    # Sync pipeline (ESP32 API)
    # ------------------------------------------------------------------

    def process_sync_query(self, query: str, session_id: str = None, user_id=None):
        self.ensure_rag_tool()
        selected_tool = "general_chat"
        tool_result = None
        is_denied = False

        q_lower = query.lower()
        for name, cfg in self.dispatcher.tools.items():
            if name in ("general_chat", "help_info"):
                continue
            if any(kw.lower() in q_lower for kw in (cfg.get("keywords") or []) if kw):
                selected_tool = name
                break

        if selected_tool != "general_chat":
            from asgiref.sync import async_to_sync
            has_access, err = async_to_sync(self._check_user_tool_access)(user_id, selected_tool)
            if not has_access:
                tool_result = err
                is_denied = True
            else:
                tool_result = self.dispatcher.tools[selected_tool]["handler"](query)

        return self.llm_processor.process_sync_query(
            query=query, session_id=session_id, selected_tool=selected_tool,
            tool_result=tool_result, is_denied=is_denied, user_id=user_id,
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_service_instance: RAGMCPService | None = None


def _get_service() -> RAGMCPService:
    global _service_instance
    if _service_instance is None:
        logger.info("[INIT] Initializing RAGMCPService...")
        try:
            _service_instance = RAGMCPService()
            logger.info("[INIT] RAGMCPService ready")
        except Exception as e:
            logger.error("[INIT] RAGMCPService failed: %s", e)
            raise
    return _service_instance


class _LazyService:
    def __getattr__(self, name):
        return getattr(_get_service(), name)


rag_mcp_service = _LazyService()

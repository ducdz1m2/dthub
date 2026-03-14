"""
RAG-MCP Integration cho DTHub AI Hub

File này đã được refactor - logic tách ra các module trong mcp_tools/:
- db_helpers.py: Database operations
- device_tools.py: IoT device control
- dictionary_tools.py: English/Japanese lookup  
- knowledge_tools.py: Wikipedia, RAG search
- science_tools.py: Physics, Chemistry
- system_tools.py: System info, weather, help
- llm_processor.py: LLM interaction
"""

import os
import sys
import json
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Get the rag-mcp directory path (parent of dthub)
rag_mcp_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'rag-mcp')
sys.path.append(rag_mcp_path)

# Import MCPDispatcher from rag-mcp với error handling
try:
    from main import MCPDispatcher
    from database import load_db
    print("[OK] Successfully imported MCPDispatcher from rag-mcp")
except Exception as e:
    print(f"[FAIL] Failed to import MCPDispatcher: {e}")
    # Create a minimal fallback dispatcher
    class MCPDispatcher:
        def __init__(self):
            self.tools = {
                "general_chat": {
                    "handler": lambda q: q,
                    "description": "General chat",
                    "keywords": []
                }
            }
        def smart_route(self, query):
            return "general_chat", 0.5
    def load_db():
        return None

# Import các module đã tách
from .mcp_tools import (
    register_device_tools,
    register_dictionary_tools,
    register_knowledge_tools,
    register_science_tools,
    register_system_tools,
)
from .mcp_tools.llm_processor import LLMProcessor
from .mcp_tools.db_helpers import get_chat_history_async, save_chat_message_async, get_chat_history_sync, save_chat_message_sync
from asgiref.sync import sync_to_async


# Mock MCP client for HTTP device control
class MockMCPClient:
    def __init__(self):
        pass
    
    def get_online_servers(self):
        return []


def get_mcp_client():
    """Get mock MCP client for HTTP system"""
    return MockMCPClient()


class RAGMCPService:
    """Service chính cho RAG-MCP integration - Kết hợp RAG và MCP một cách hài hòa"""

    def __init__(self):
        try:
            self.dispatcher = MCPDispatcher()
        except Exception as e:
            print(f"[FAIL] Failed to create MCPDispatcher: {e}")
            self.dispatcher = MCPDispatcher()  # Fallback to minimal dispatcher
        
        self.vectorstore = None
        self.retriever = None
        self.llm_processor = None
        
        self._load_vector_database()
        self._init_llm_processor()
        
        # Register all tools
        try:
            self._register_all_tools()
        except Exception as e:
            print(f"[FAIL] Failed to register tools: {e}")

    def _load_vector_database(self):
        """Load vector database cho RAG"""
        try:
            self.vectorstore = load_db()
            self.retriever = self.vectorstore.as_retriever(search_kwargs={"k": 3, "fetch_k": 8})
            print("Vector database loaded successfully")
        except Exception as e:
            print(f"Vector database not available: {e}")
            self.retriever = None
    
    def _init_llm_processor(self):
        """Initialize LLM processor với config từ AI service"""
        try:
            from .ai_service import get_ai_service
            ai_service = get_ai_service()
            self.llm_processor = LLMProcessor(
                llm_model=ai_service.config.llm_model,
                temperature=ai_service.config.llm_temperature,
                max_tokens=ai_service.config.llm_max_tokens
            )
            print("LLM processor initialized successfully")
        except Exception as e:
            print(f"[FAIL] Failed to initialize LLM processor: {e}")
            # Fallback values
            self.llm_processor = LLMProcessor(
                llm_model="llama3.2",
                temperature=0.7,
                max_tokens=2048
            )
    
    def _register_all_tools(self):
        """Đăng ký tất cả các tools từ các module và đồng bộ với Database"""
        # Knowledge tools (RAG, Wikipedia)
        register_knowledge_tools(self.dispatcher, self.retriever)
        
        # Device tools (IoT control, list devices)
        register_device_tools(self.dispatcher)
        
        # Dictionary tools (English, Japanese)
        register_dictionary_tools(self.dispatcher)
        
        # Science tools (Physics, Chemistry)
        register_science_tools(self.dispatcher)
        
        # System tools (system info, weather, help)
        register_system_tools(self.dispatcher)
        
        # ĐỒNG BỘ TOOLS VỚI DATABASE (Auto-registration)
        try:
            from .models import MCPTool
            for name, config in self.dispatcher.tools.items():
                display_name = config.get('display_name', name.replace('_', ' ').title())
                description = config.get('description', f"Tool {name}")
                keywords = config.get('keywords', [])
                
                # Các tool hệ thống mặc định (Chỉ giữ lại những thứ cốt yếu nhất)
                is_system = name in {"general_chat", "help_info", "tool_metadata"}
                is_public = not is_system # Các tool còn lại (gồm cả system_info) là public để user tự thêm
                
                MCPTool.objects.update_or_create(
                    name=name,
                    defaults={
                        'display_name': display_name,
                        'description': description,
                        'keywords': keywords,
                        'is_system': is_system,
                        'is_public': is_public,
                        'is_enabled': True,
                        'is_visible': True
                    }
                )
            print("[OK] All MCP tools synchronized with Database")
        except Exception as e:
            print(f"[FAIL] Failed to sync tools with DB: {e}")
        
        print("All MCP tools registered successfully")

    def _check_metadata_query(self, query):
        """Pre-filter to check if query is asking about tool metadata/source (highest priority)"""
        query_lower = query.lower()
        
        # Metadata-indicating patterns
        metadata_patterns = [
            "lấy ở đâu", "từ đâu ra", "nguồn", "cách hoạt động", 
            "cơ chế", "dữ liệu từ đâu", "thông tin này ở đâu", 
            "ai lấy từ đâu", "lấy thông tin ở đâu", "dữ liệu ở đâu",
            "source of", "how does", "where do you get"
        ]
        
        # Check if query matches metadata patterns
        is_metadata_question = any(pattern in query_lower for pattern in metadata_patterns)
        
        if is_metadata_question and "tool_metadata" in self.dispatcher.tools:
            # Also check that a tool name is mentioned
            tool_keywords = {
                "thời tiết": "weather", "weather": "weather",
                "wikipedia": "wikipedia", "wiki": "wikipedia",
                "từ điển": "dictionary", "dictionary": "dictionary",
                "tiếng anh": "dictionary", "tiếng nhật": "dictionary",
                "thiết bị": "device", "device": "device",
                "rag": "rag", "tài liệu": "rag",
                "vật lý": "physics", "physics": "physics",
                "hóa học": "chemistry", "chemistry": "chemistry",
                "hệ thống": "system", "system": "system",
                "ai": "llm", "llm": "llm", "model": "llm"
            }
            
            for keyword, tool_key in tool_keywords.items():
                if keyword in query_lower:
                    return "tool_metadata"
        
        return None

    async def _check_user_tool_access(self, user_id, tool_name):
        """
        Kiểm tra quyền truy cập công cụ MCP (Xác thực & Ủy quyền).
        CHỈ những tool đã được thêm vào bộ sưu tập của user (UserMCPTool) mới được sử dụng.
        NGOẠI LỆ: Các công cụ hệ thống (is_system=True) luôn được phép.
        """
        if not user_id:
            logger.warning(f"[AUTH_FAILED] Truy cập tool '{tool_name}' bị từ chối: User chưa đăng nhập")
            return False, "403: Không có quyền thực thi. Bạn cần đăng nhập để sử dụng công cụ này."
        
        try:
            from .models import MCPTool, UserMCPTool
            
            # Sử dụng sync_to_async cho truy vấn database
            @sync_to_async
            def check_db():
                # 1. Kiểm tra nếu là tool hệ thống (mặc định cho mọi user)
                try:
                    tool_obj = MCPTool.objects.get(name=tool_name, is_enabled=True)
                    if tool_obj.is_system:
                        return True, None
                except MCPTool.DoesNotExist:
                    return False, f"404: Công cụ '{tool_name}' không tồn tại hoặc bị vô hiệu hóa."

                # 2. Kiểm tra nếu user đã thêm tool này vào bộ sưu tập chưa
                has_access = UserMCPTool.objects.filter(
                    user_id=user_id,
                    tool=tool_obj,
                    is_active=True
                ).exists()
                
                if not has_access:
                    logger.error(f"[ACCESS_DENIED] User {user_id} cố gắng truy cập tool '{tool_name}' mà không có quyền")
                    return False, f"403: Không có quyền thực thi. Công cụ '{tool_name}' chưa được thêm vào bộ sưu tập của bạn."
                
                return True, None

            return await check_db()
            
        except Exception as e:
            logger.exception(f"[SYSTEM_ERROR] Lỗi kiểm tra quyền cho user {user_id} với tool {tool_name}")
            return False, f"500: Lỗi hệ thống khi kiểm tra quyền: {str(e)}"

    async def _get_user_ai_config(self, user_id):
        """Lấy cấu hình AI của User (hoặc mặc định)"""
        from .models import AIConfiguration
        try:
            config = await sync_to_async(AIConfiguration.objects.filter(user_id=user_id, is_default=True, is_active=True).first)()
            if not config:
                config = await sync_to_async(AIConfiguration.objects.filter(user__isnull=True, is_default=True, is_active=True).first)()
            return config
        except Exception:
            return None

    async def process_websocket_query(self, consumer, query, session_id=None):
        """Xử lý query từ WebSocket (Nâng cấp Agentic MCP)"""
        from .models import MCPTool, ChatMessage
        from .mcp_client import MCPDiscoveryClient
        
        # Lấy user_id từ consumer scope
        scope_user = getattr(consumer, "scope", {}).get("user") if consumer else None
        user_id = scope_user.id if scope_user and getattr(scope_user, "is_authenticated", False) else None
        
        # 0. Cấu hình AI
        ai_config = await self._get_user_ai_config(user_id)
        if ai_config:
            self.llm_processor.llm_model = ai_config.llm_model
            self.llm_processor.temperature = ai_config.llm_temperature
            self.llm_processor.max_tokens = ai_config.llm_max_tokens
            self.llm_processor.response_language = ai_config.response_language
        
        # Gửi tín hiệu đang lập kế hoạch
        if hasattr(consumer, 'send'):
            await consumer.send(text_data=json.dumps({
                "type": "response", "query": query, "debug": "Đang lập kế hoạch thực thi...", "done": False
            }, ensure_ascii=False))

        # 1. DECOMPOSITION - Lập kế hoạch
        # Lấy danh sách tools mà user có quyền dùng
        @sync_to_async
        def get_user_tools():
            from .models import UserMCPTool
            system_tools = list(MCPTool.objects.filter(is_system=True, is_enabled=True))
            if user_id:
                user_tools = list(MCPTool.objects.filter(user_assignments__user_id=user_id, user_assignments__is_active=True, is_enabled=True))
                return system_tools + user_tools
            return system_tools

        available_tools = await get_user_tools()
        logger.info(f"[AGENTIC_MCP] Available tools: {[t.name for t in available_tools]}")
        
        chat_history = await get_chat_history_async(session_id or "default", limit=5, user_id=user_id)
        
        plan = await self.llm_processor.generate_plan(query, chat_history, available_tools)
        logger.info(f"[AGENTIC_MCP] Plan: {plan}")
        
        # 2. EXECUTION - Thực thi song song
        results = []
        for task in plan:
            tool_name = task.get('tool')
            params = task.get('parameters', {})
            
            if tool_name == "general_chat":
                results.append({"tool": tool_name, "result": "No specific tool needed"})
                continue

            logger.info(f"[AGENTIC_MCP] Executing: {tool_name} with {params}")
            if hasattr(consumer, 'send'):
                await consumer.send(text_data=json.dumps({
                    "type": "response", "debug": f"Đang thực thi: {tool_name}...", "done": False
                }, ensure_ascii=False))

            # Thực thi tool (External MCP hoặc Built-in)
            try:
                # Tìm tool trong DB
                @sync_to_async
                def find_tool(name):
                    return MCPTool.objects.filter(name=name).first()
                
                tool_obj = await find_tool(tool_name)
                
                if not tool_obj:
                    logger.warning(f"[AGENTIC_MCP] Tool not found in DB: {tool_name}")
                    results.append({"tool": tool_name, "result": f"Lỗi: Không tìm thấy tool {tool_name}"})
                    continue

                if tool_obj.tool_type == 'external_api':
                    # Gọi MCP Server từ xa
                    res = await sync_to_async(MCPDiscoveryClient.execute_remote_tool)(tool_name, params)
                    results.append({"tool": tool_name, "result": res})
                else:
                    # Gọi Built-in tool qua dispatcher cũ
                    if tool_name in self.dispatcher.tools:
                        handler = self.dispatcher.tools[tool_name]["handler"]
                        if tool_name == "rag_search":
                            res = await sync_to_async(handler)(params.get('query', query), self.retriever)
                        else:
                            res = await sync_to_async(handler)(query if not params else params)
                        results.append({"tool": tool_name, "result": res})
                    else:
                        logger.warning(f"[AGENTIC_MCP] Handler not found in dispatcher: {tool_name}")
                        results.append({"tool": tool_name, "result": f"Lỗi: Handler cho {tool_name} chưa được đăng ký"})
            except Exception as e:
                logger.error(f"[AGENTIC_MCP] Execution error for {tool_name}: {e}")
                results.append({"tool": tool_name, "result": f"Lỗi thực thi: {str(e)}"})

        # 3. SYNTHESIS - Tổng hợp
        logger.info(f"[AGENTIC_MCP] Synthesizing response for results: {len(results)}")
        final_response = await self.llm_processor.synthesize_response(query, results, self.llm_processor.response_language)
        
        # 4. TRẢ VỀ & LƯU DB
        if hasattr(consumer, 'send'):
            # Gửi từng chunk nếu muốn streaming (ở đây làm đơn giản gửi cả cục)
            await consumer.send(text_data=json.dumps({
                "type": "chunk", "chunk": final_response, "done": False
            }, ensure_ascii=False))
            
            await consumer.send(text_data=json.dumps({
                "type": "response", "done": True, "full_response": final_response,
                "tool_used": "agentic_mcp", "response_time": 0.0 # Cần tính thực tế
            }, ensure_ascii=False))

        await save_chat_message_async(session_id, query, final_response, "agentic_mcp", user_id=user_id)
        return final_response

    def process_sync_query(self, query, session_id=None, user_id=None):
        """Phiên bản đồng bộ dành cho API ESP32"""
        from .ai_service import get_ai_service
        from asgiref.sync import async_to_sync
        
        # 1. Routing
        selected_tool, _ = self.dispatcher.smart_route(query)
        ai_service = get_ai_service()
        
        # Update LLM processor config
        self.llm_processor.llm_model = ai_service.config.llm_model
        self.llm_processor.temperature = ai_service.config.llm_temperature
        
        # 2. Tool Execution & Permission Check
        tool_result = None
        is_denied = False
        if selected_tool != "general_chat":
            # Kiểm tra quyền truy cập (sync version)
            has_access, error_msg = async_to_sync(self._check_user_tool_access)(user_id, selected_tool)
            
            if not has_access:
                tool_result = error_msg
                is_denied = True
            else:
                handler = self.dispatcher.tools[selected_tool]["handler"]
                if selected_tool == "rag_search":
                    tool_result = handler(query, self.retriever)
                else:
                    tool_result = handler(query)

        # 3. LLM Interaction
        return self.llm_processor.process_sync_query(
            query=query,
            session_id=session_id,
            selected_tool=selected_tool,
            tool_result=tool_result,
            is_denied=is_denied,
            user_id=user_id
        )


# Khởi tạo service với error handling
try:
    print("[INIT] Initializing RAG-MCP Service...")
    rag_mcp_service = RAGMCPService()
    print("[OK] RAG-MCP Service initialized successfully")
except Exception as e:
    print(f"[FAIL] Failed to initialize RAG-MCP Service: {e}")
    import traceback
    traceback.print_exc()
    # Create a minimal fallback service
    class MinimalRAGMCPService:
        def __init__(self):
            self.dispatcher = MCPDispatcher()
            self.retriever = None
        async def process_websocket_query(self, consumer, query, session_id=None):
            return "Xin lỗi, hệ thống AI đang gặp sự cố khởi tạo. Vui lòng thử lại sau."
        def process_sync_query(self, query, session_id=None):
            return "Xin lỗi, hệ thống AI đang gặp sự cố khởi tạo. Vui lòng thử lại sau.", "error"
    rag_mcp_service = MinimalRAGMCPService()

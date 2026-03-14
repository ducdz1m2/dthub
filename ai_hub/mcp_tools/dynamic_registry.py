"""
Dynamic MCP Tool Registry - Hệ thống đăng ký tool động từ database
"""
import json
import requests
from asgiref.sync import sync_to_async


class DynamicMCPRegistry:
    """Registry động cho MCP tools - load từ database"""
    
    def __init__(self):
        self._tools_cache = {}
        self._last_refresh = None
    
    def _load_tools_from_db(self):
        """Load enabled tools from database"""
        try:
            from ..models import MCPTool
            tools = MCPTool.objects.filter(is_enabled=True)
            
            registry = {}
            for tool in tools:
                registry[tool.name] = {
                    'name': tool.name,
                    'display_name': tool.display_name,
                    'description': tool.description,
                    'tool_type': tool.tool_type,
                    'keywords': tool.keywords_list,
                    'handler': None,  # Will be resolved dynamically
                    'module_path': tool.module_path,
                    'function_name': tool.function_name,
                    'api_endpoint': tool.api_endpoint,
                    'api_method': tool.api_method,
                    'api_headers': tool.api_headers,
                    'priority': tool.priority,
                    'icon': tool.icon,
                    'color_class': tool.color_class,
                    'category': tool.category,
                    'is_visible': tool.is_visible,
                }
            return registry
        except Exception as e:
            print(f"[ERROR] Failed to load tools from DB: {e}")
            return {}
    
    def get_all_tools(self):
        """Get all enabled tools from database"""
        return self._load_tools_from_db()
    
    def get_visible_tools(self):
        """Get tools that should be displayed in UI"""
        all_tools = self._load_tools_from_db()
        return {k: v for k, v in all_tools.items() if v.get('is_visible', True)}
    
    def get_tool_handler(self, tool_name):
        """Get handler function for a tool"""
        tools = self._load_tools_from_db()
        tool_config = tools.get(tool_name)
        
        if not tool_config:
            return None
        
        tool_type = tool_config.get('tool_type')
        
        if tool_type == 'builtin':
            return self._get_builtin_handler(tool_config)
        elif tool_type == 'external_api':
            return self._get_api_handler(tool_config)
        else:
            return None
    
    def _get_builtin_handler(self, tool_config):
        """Import and return built-in handler function"""
        try:
            import importlib
            module_path = tool_config.get('module_path')
            function_name = tool_config.get('function_name')
            
            if not module_path or not function_name:
                return None
            
            # Import module
            if module_path.startswith('.'):
                # Relative import from mcp_tools
                full_path = f'ai_hub.mcp_tools{module_path}'
            else:
                full_path = module_path
            
            module = importlib.import_module(full_path)
            handler = getattr(module, function_name, None)
            return handler
        except Exception as e:
            print(f"[ERROR] Failed to load builtin handler {tool_config.get('name')}: {e}")
            return None
    
    def _get_api_handler(self, tool_config):
        """Create handler function for external API tool"""
        def api_handler(query):
            try:
                endpoint = tool_config.get('api_endpoint')
                method = tool_config.get('api_method', 'GET')
                headers = tool_config.get('api_headers', {})
                
                if method == 'GET':
                    response = requests.get(
                        endpoint, 
                        headers=headers, 
                        params={'query': query},
                        timeout=10
                    )
                else:
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        json={'query': query},
                        timeout=10
                    )
                
                if response.status_code == 200:
                    return response.json()
                return f"API Error: {response.status_code}"
            except Exception as e:
                return f"Error calling API: {str(e)}"
        
        return api_handler


# Singleton instance
registry = DynamicMCPRegistry()


def get_dynamic_tools_for_api():
    """Get tools list for API response (UI display)"""
    tools = registry.get_visible_tools()
    return [
        {
            'name': t['name'],
            'display_name': t['display_name'],
            'description': t['description'],
            'icon': t.get('icon', 'fa-terminal'),
            'color_class': t.get('color_class', 'border-info text-info'),
            'category': t.get('category', 'General'),
            'keywords': t.get('keywords', []),
        }
        for t in tools.values()
    ]


@sync_to_async
def get_dynamic_tools_async():
    """Async version for use in consumers"""
    return get_dynamic_tools_for_api()

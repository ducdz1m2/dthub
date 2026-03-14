from django.apps import AppConfig


class AiHubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai_hub'
    verbose_name = 'AI Hub'

    def ready(self):
        # Import signals
        import ai_hub.signals
        
        # Initialize MCP client when Django starts - OPTIMIZED
        # Only initialize if not running migrations and running server
        import sys
        if ('migrate' in sys.argv or 'makemigrations' in sys.argv or 
            'collectstatic' in sys.argv or 'runserver' not in sys.argv):
            return
            
        try:
            from .mcp_client import initialize_mcp_client
            # Initialize in background without delay to avoid blocking startup
            import threading
            
            def delayed_init():
                try:
                    initialize_mcp_client()
                except Exception as e:
                    # Fail silently if initialization fails
                    print(f"Warning: MCP client initialization failed: {e}")
            
            thread = threading.Thread(target=delayed_init, daemon=True)
            thread.start()
        except Exception as e:
            # Fail silently if initialization fails during migrations
            print(f"Warning: MCP client initialization setup failed: {e}")

import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dthub.settings')
django.setup()

from ai_hub.models import MCPTool

tools = list(MCPTool.objects.all())
print(f"Found {len(tools)} tools")
for t in tools:
    print(f"TOOL: {t.name} | DESC: {t.description}")

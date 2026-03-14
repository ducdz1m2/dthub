import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dthub.settings')
django.setup()

from ai_hub.models import MCPTool

for t in MCPTool.objects.all():
    print(f"TOOL: {t.name}")
    print(f"DESC: {t.description}")
    print("-" * 20)

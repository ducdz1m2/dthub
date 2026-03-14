from django.core.management.base import BaseCommand
from django.utils import timezone

from ai_hub.models import MCPServer


class Command(BaseCommand):
    help = "Seed sample MCP servers for local testing"

    def handle(self, *args, **options):
        samples = [
            {
                "name": "Chemistry MCP (Local)",
                "device_id": "chem_local_9101",
                "domain": "http://127.0.0.1:9101",
                "server_type": "private",
                "connection_method": "http",
                "description": "Local chemistry MCP server (demo).",
                "location": "localhost",
            },
            {
                "name": "Physics MCP (Local)",
                "device_id": "physics_local_9102",
                "domain": "http://127.0.0.1:9102",
                "server_type": "private",
                "connection_method": "http",
                "description": "Local physics MCP server (demo).",
                "location": "localhost",
            },
        ]

        created = 0
        updated = 0

        for s in samples:
            obj, was_created = MCPServer.objects.update_or_create(
                device_id=s["device_id"],
                defaults={
                    "name": s["name"],
                    "domain": s["domain"],
                    "server_type": s["server_type"],
                    "connection_method": s["connection_method"],
                    "description": s["description"],
                    "location": s["location"],
                    "is_active": True,
                    "last_seen": timezone.now(),
                },
            )
            if was_created:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Seed completed: created={created}, updated={updated}"))


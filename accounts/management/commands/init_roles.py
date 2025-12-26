from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

ROLE_MAP = {
    "ProductOrderManager": [
        "manage_product",
        "manage_order",
    ],
     "ContentFeedbackManager": [
        "manage_post",
        "manage_feedback",
    ],
    "AIArchitect": [
        "manage_ai_architecture",
    ],
}

class Command(BaseCommand):
    def handle(self, *args, **kwargs):
        for group_name, perms in ROLE_MAP.items():
            group, _ = Group.objects.get_or_create(name=group_name)
            for codename in perms:
                perm = Permission.objects.get(codename=codename)
                group.permissions.add(perm)
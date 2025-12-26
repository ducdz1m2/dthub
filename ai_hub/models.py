from django.db import models

class AIConfig(models.Model):
    name = models.CharField(max_length=255)
    endpoint = models.URLField()

    class Meta:
        permissions = [
            ("manage_ai_architecture", "Can manage AI architecture"),
        ]

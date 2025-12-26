from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
            permissions = [
                  ("manage_product", "Can manage product"),
            ]

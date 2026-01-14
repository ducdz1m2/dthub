from django.db import models

class Product(models.Model):
    PRODUCT_TYPES = [
        ('iot', 'IoT Device'),
        ('mcu', 'Microcontroller'),
    ]

    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPES)
    description = models.TextField(blank=True)
    datasheet_url = models.URLField(blank=True)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        permissions = [
            ("manage_product", "Can manage products")
        ]

    def __str__(self):
        return self.name

# Model để lưu nhiều ảnh cho 1 sản phẩm
class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    alt_text = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.product.name} - {self.alt_text or 'Image'}"

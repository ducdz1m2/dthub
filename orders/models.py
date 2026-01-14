from django.db import models
from django.conf import settings
from products.models import Product

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Chờ duyệt'),
        ('Surveying', 'Khảo sát thực tế'),
        ('Designing', 'Lên bản vẽ hệ thống'),
        ('Deploying', 'Đang lắp đặt/Thi công'),
        ('Completed', 'Nghiệm thu & Bàn giao'),
        ('Cancelled', 'Hủy đơn'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Khách hàng")
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    total = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    # --- CÁC TRƯỜNG MỚI THÊM ---
    address = models.CharField(max_length=255, verbose_name="Địa chỉ lắp đặt", null=True, blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='tasks',
        verbose_name="Kỹ thuật phụ trách"
    )
    note = models.TextField(verbose_name="Ghi chú kỹ thuật", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Đơn hàng #{self.id} - {self.product.name}"
    @property
    def is_locked(self):
        """Kiểm tra xem đơn hàng đã kết thúc chưa (không cho sửa trạng thái)"""
        return self.status in ['Completed', 'Cancelled']
    

class Review(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='review')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(default=5, choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(verbose_name="Nội dung đánh giá")
    image = models.ImageField(upload_to='reviews/', null=True, blank=True, verbose_name="Hình ảnh thực tế")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return f"Đánh giá cho Đơn #{self.order.id}"
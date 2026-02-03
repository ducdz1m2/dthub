from django.db import models
from django.conf import settings
from django.utils import timezone
from products.models import Product
import uuid

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
    
    @property
    def is_paid(self):
        """Kiểm tra xem đơn hàng đã được thanh toán chưa"""
        return hasattr(self, 'payment') and self.payment.is_paid if hasattr(self, 'payment') else False
    
    @property
    def payment_status(self):
        """Lấy trạng thái thanh toán"""
        if not hasattr(self, 'payment'):
            return 'Chưa thanh toán'
        return self.payment.get_status_display()

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


class Payment(models.Model):
    """Model quản lý thanh toán cho đơn hàng"""
    PAYMENT_STATUS = [
        ('pending', 'Chờ thanh toán'),
        ('processing', 'Đang xử lý'),
        ('completed', 'Hoàn thành'),
        ('failed', 'Thất bại'),
        ('refunded', 'Đã hoàn tiền'),
        ('cancelled', 'Đã hủy'),
    ]
    
    PAYMENT_METHODS = [
        ('vnpay', 'VNPay'),
        ('cod', 'Ship COD'),
        ('bank_transfer', 'Chuyển khoản'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    method = models.CharField(max_length=20, choices=PAYMENT_METHODS, verbose_name="Phương thức thanh toán")
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending', verbose_name="Trạng thái")
    amount = models.DecimalField(max_digits=12, decimal_places=0, verbose_name="Số tiền")
    
    # VNPay specific fields
    transaction_id = models.CharField(max_length=100, blank=True, null=True, verbose_name="Mã giao dịch")
    vnpay_transaction_no = models.CharField(max_length=50, blank=True, null=True, verbose_name="Số giao dịch VNPay")
    vnpay_bank_code = models.CharField(max_length=20, blank=True, null=True, verbose_name="Ngân hàng")
    vnpay_card_type = models.CharField(max_length=20, blank=True, null=True, verbose_name="Loại thẻ")
    
    # Gateway response for debugging
    gateway_response = models.JSONField(default=dict, blank=True, verbose_name="Phản hồi từ gateway")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày tạo")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Cập nhật lần cuối")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Ngày hoàn thành")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Thanh toán"
        verbose_name_plural = "Thanh toán"
    
    def __str__(self):
        return f"Thanh toán {self.get_method_display()} - Đơn #{self.order.id}"
    
    @property
    def is_paid(self):
        """Kiểm tra xem đã thanh toán chưa"""
        return self.status == 'completed'
    
    def mark_completed(self, transaction_id=None):
        """Đánh dấu thanh toán hoàn thành"""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if transaction_id:
            self.transaction_id = transaction_id
        self.save()
from django.db import models
from django.conf import settings

class SupportRequest(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Chờ xử lý'),
        ('In_Progress', 'Đang xử lý'),
        ('Resolved', 'Đã giải quyết'),
        ('Closed', 'Đã đóng'),
    ]
    
    PRIORITY_CHOICES = [
        ('Low', 'Thấp'),
        ('Medium', 'Trung bình'),
        ('High', 'Cao'),
        ('Urgent', 'Khẩn cấp'),
    ]
    
    CATEGORY_CHOICES = [
        ('Technical', 'Hỗ trợ kỹ thuật'),
        ('Installation', 'Hỗ trợ lắp đặt'),
        ('Product', 'Sản phẩm'),
        ('Billing', 'Thanh toán'),
        ('Other', 'Khác'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Người yêu cầu")
    title = models.CharField(max_length=200, verbose_name="Tiêu đề")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='Technical', verbose_name="Danh mục")
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='Medium', verbose_name="Mức độ ưu tiên")
    description = models.TextField(verbose_name="Mô tả chi tiết")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending', verbose_name="Trạng thái")
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='assigned_support_requests',
        verbose_name="Nhân viên phụ trách"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Yêu cầu #{self.id} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ('manage_support_request', 'Can manage support requests'),
        ]

class SupportResponse(models.Model):
    support_request = models.ForeignKey(SupportRequest, on_delete=models.CASCADE, related_name='responses')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField(verbose_name="Nội dung phản hồi")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Phản hồi cho yêu cầu #{self.support_request.id}"

class SupportAttachment(models.Model):
    support_request = models.ForeignKey(SupportRequest, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='support_attachments/', verbose_name="File đính kèm")
    filename = models.CharField(max_length=255, verbose_name="Tên file")
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"File đính kèm cho yêu cầu #{self.support_request.id}"

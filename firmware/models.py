from django.db import models

class FirmwareFile(models.Model):
    DEVICE_CHOICES = [
        ('ESP32', 'ESP32'),
        ('ESP8266', 'ESP8266'),
        ('Arduino', 'Arduino'),
        ('Raspberry_Pi', 'Raspberry Pi'),
        ('Other', 'Khác'),
    ]
    
    name = models.CharField(max_length=200, verbose_name="Tên firmware")
    device_type = models.CharField(max_length=20, choices=DEVICE_CHOICES, default='ESP32', verbose_name="Loại thiết bị")
    version = models.CharField(max_length=50, verbose_name="Phiên bản")
    description = models.TextField(verbose_name="Mô tả")
    bin_file = models.FileField(upload_to='firmware/', verbose_name="File .bin")
    manifest_file = models.FileField(upload_to='firmware/manifests/', verbose_name="File manifest.json")
    
    is_active = models.BooleanField(default=True, verbose_name="Kích hoạt")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.get_device_type_display()})"
    
    class Meta:
        ordering = ['-created_at']

class FlashingSession(models.Model):
    firmware = models.ForeignKey(FirmwareFile, on_delete=models.CASCADE, verbose_name="Firmware")
    user_ip = models.GenericIPAddressField(verbose_name="IP người dùng")
    user_agent = models.TextField(verbose_name="User Agent")
    flashed_at = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False, verbose_name="Thành công")
    error_message = models.TextField(null=True, blank=True, verbose_name="Lỗi")
    
    def __str__(self):
        return f"Flash session for {self.firmware.name} at {self.flashed_at}"

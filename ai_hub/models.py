from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
import secrets

User = get_user_model()

class MCPServer(models.Model):
    """Model cho MCP Servers"""
    name = models.CharField(max_length=200, verbose_name="Tên Server")
    device_id = models.CharField(max_length=100, unique=True, verbose_name="Device ID")
    
    # Thay vì IP trực tiếp, dùng domain/subdomain
    domain = models.CharField(max_length=255, blank=True, null=True, verbose_name="Domain")
    subdomain = models.CharField(max_length=100, unique=True, blank=True, null=True, verbose_name="Subdomain")
    
    # Loại server
    server_type = models.CharField(max_length=20, choices=[
        ('private', 'Private Server'),
        ('public', 'Public Server')
    ], default='private', verbose_name="Loại Server")
    
    # Chủ sở hữu (chỉ cho private server)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        verbose_name="Chủ sở hữu"
    )
    
    # Thông tin kết nối (ẩn đi IP)
    connection_method = models.CharField(max_length=20, choices=[
        ('http', 'HTTP Direct'),
        ('ddns', 'Dynamic DNS'),
        ('vpn', 'VPN Tunnel'),
        ('cloudflare', 'Cloudflare Tunnel')
    ], default='http', verbose_name="Phương thức kết nối")
    
    # Token bảo mật
    auth_token = models.CharField(max_length=128, unique=True, verbose_name="Token xác thực")
    api_key = models.CharField(max_length=128, unique=True, blank=True, verbose_name="API Key")
    
    # Metadata
    description = models.TextField(blank=True, verbose_name="Mô tả")
    location = models.CharField(max_length=200, blank=True, verbose_name="Vị trí")
    is_active = models.BooleanField(default=True, verbose_name="Hoạt động")
    is_public = models.BooleanField(default=False, verbose_name="Công khai")
    
    # New fields for Code Editor and Managed MCP
    is_local_managed = models.BooleanField(default=False, verbose_name="Tự quản lý code")
    code_template = models.TextField(blank=True, verbose_name="Code Server (FastAPI Template)")
    last_test_log = models.TextField(blank=True, verbose_name="Logs chạy thử")
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        permissions = [
            ("manage_mcp_servers", "Can manage MCP servers"),
        ]
        verbose_name = "MCP Server"
        verbose_name_plural = "MCP Servers"
    
    def __str__(self):
        return f"{self.name} ({self.device_id})"
    
    def save(self, *args, **kwargs):
        # Tự động tạo subdomain cho public server
        if self.server_type == 'public' and not self.subdomain:
            self.subdomain = f"{self.device_id.lower()}.mcp.dthub.com"
        
        # Tạo token nếu chưa có
        if not self.auth_token:
            self.auth_token = secrets.token_urlsafe(64)
        if not self.api_key:
            self.api_key = secrets.token_urlsafe(64)
            
        super().save(*args, **kwargs)
    
    @property
    def get_endpoint(self):
        """Lấy endpoint để kết nối"""
        if self.domain:
            domain = (self.domain or "").strip().rstrip("/")
            if domain.startswith("http://") or domain.startswith("https://"):
                return domain
            if self.connection_method == 'http':
                return f"http://{domain}"
            return f"https://{domain}"
        if self.subdomain:
            subdomain = (self.subdomain or "").strip().rstrip("/")
            if subdomain.startswith("http://") or subdomain.startswith("https://"):
                return subdomain
            return f"https://{subdomain}"
        return None

class ESP32Device(models.Model):
    """Model cho ESP32 devices"""
    device_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    device_type = models.CharField(max_length=50, choices=[
        ('sensor', 'Sensor Node'),
        ('actuator', 'Actuator Node'),
        ('hybrid', 'Sensor + Actuator')
    ])
    # MQTT topic không còn dùng
    # mqtt_topic = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField(null=True, blank=True, help_text="IP address of the device")
    location = models.CharField(max_length=200, blank=True)
    auth_token = models.CharField(max_length=64, unique=True, blank=True, help_text="Unique token for device authentication")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    
    @property
    def is_online(self):
        """Check if device has been seen in the last 5 minutes"""
        if not self.last_seen:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return self.last_seen >= timezone.now() - timedelta(minutes=5)

    def __str__(self):
        return f"{self.name} ({self.device_id})"
    
    def save(self, *args, **kwargs):
        # Generate token if not exists
        if not self.auth_token:
            self.auth_token = self.generate_token()
        
        # Không cần tạo MQTT topic nữa
        # if not self.mqtt_topic:
        #     self.mqtt_topic = f'esp32/{self.device_id}/sensor_data'
            
        super().save(*args, **kwargs)
    
    def generate_token(self):
        """Generate a unique authentication token based on device_id and MAC address"""
        # Use device_id + random bytes for uniqueness
        base_string = f"{self.device_id}_{secrets.token_hex(8)}"
        return secrets.token_urlsafe(48)  # 64-character token
    
    @classmethod
    def authenticate_by_token(cls, token):
        """Authenticate device by token"""
        try:
            return cls.objects.get(auth_token=token, is_active=True)
        except cls.DoesNotExist:
            return None

class SensorData(models.Model):
    """Model cho sensor data từ ESP32"""
    device = models.ForeignKey(ESP32Device, on_delete=models.CASCADE)
    sensor_type = models.CharField(max_length=50, choices=[
        ('temperature', 'Temperature'),
        ('humidity', 'Humidity'),
        ('light', 'Light'),
        ('motion', 'Motion'),
        ('soil_moisture', 'Soil Moisture'),
        ('ph', 'pH Level'),
    ])
    value = models.FloatField()
    unit = models.CharField(max_length=20, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['device', 'sensor_type', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.device.name} - {self.sensor_type}: {self.value}{self.unit}"

class DeviceCommand(models.Model):
    """Model cho commands gửi đến ESP32"""
    device = models.ForeignKey(ESP32Device, on_delete=models.CASCADE)
    command = models.CharField(max_length=100)
    parameters = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('executed', 'Executed'),
        ('failed', 'Failed'),
    ], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    executed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.device.name} - {self.command}"

class DeviceControlLabel(models.Model):
    """Model để gán nhãn cho các chân điều khiển (Relay/GPIO) của thiết bị"""
    device = models.ForeignKey(ESP32Device, on_delete=models.CASCADE, related_name='labels')
    channel = models.CharField(max_length=50, help_text="Tên kênh (VD: relay1, gpio2)")
    label = models.CharField(max_length=100, help_text="Nhãn hiển thị (VD: Quạt, Đèn chùm)")
    is_active = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ('device', 'channel')
        verbose_name = "Device Label"
        verbose_name_plural = "Device Labels"

    def __str__(self):
        return f"{self.device.name} - {self.channel}: {self.label}"

class ChatSession(models.Model):
    """Model cho chat sessions với AI (Web & ESP32)"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    device = models.ForeignKey(
        'ESP32Device', 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='chat_sessions'
    )
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Thời gian hết hạn của session")
    is_active = models.BooleanField(default=True)
    
    def is_valid(self):
        """Kiểm tra session còn hạn không"""
        from django.utils import timezone
        if not self.is_active:
            return False
        if self.expires_at and timezone.now() > self.expires_at:
            return False
        return True

    def __str__(self):
        owner = self.user.username if self.user else (self.device.name if self.device else 'Unknown')
        return f"Session {self.session_id} - {owner}"

class ChatMessage(models.Model):
    """Model cho chat messages"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    query = models.TextField()
    response = models.TextField()
    tool_used = models.CharField(max_length=50)
    response_time = models.FloatField(help_text="Response time in seconds")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.session.session_id} - {self.tool_used}"

class AIConfiguration(models.Model):
    """Model để lưu cấu hình AI cho chatbot (đơn giản hóa)"""
    name = models.CharField(max_length=100, verbose_name="Tên cấu hình")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        null=True, blank=True,
        help_text="Để trống cho cấu hình mặc định"
    )
    is_default = models.BooleanField(default=False, verbose_name="Mặc định")
    is_active = models.BooleanField(default=True, verbose_name="Hoạt động")
    
    # STT Configuration
    STT_ENGINE_CHOICES = [
        ('vosk', 'Vosk (Offline - Siêu nhẹ)'),
        ('whisper', 'OpenAI Whisper (Local - Thông minh)'),
        ('custom', 'Custom STT API (Tùy chỉnh)'),
    ]
    stt_engine = models.CharField(
        max_length=20, 
        choices=STT_ENGINE_CHOICES, 
        default='vosk', 
        verbose_name="Speech-to-Text Engine"
    )
    stt_custom_url = models.CharField(
        max_length=255, 
        blank=True, null=True, 
        verbose_name="Custom STT API URL",
        help_text="Ví dụ: http://localhost:5000/stt"
    )
    
    stt_language = models.CharField(max_length=10, choices=[
        ('vi-VN', 'Tiếng Việt'),
        ('en-US', 'Tiếng Anh'),
        ('ja-JP', 'Tiếng Nhật'),
    ], default='vi-VN', verbose_name="Ngôn ngữ STT")
    
    # LLM Configuration (chỉ Ollama)
    llm_model = models.CharField(max_length=100, default='qwen2.5:1.5b', verbose_name="Model AI")
    llm_temperature = models.FloatField(default=0.1, verbose_name="Độ sáng tạo (0-2)")
    llm_max_tokens = models.IntegerField(default=250, verbose_name="Độ dài trả lời tối đa")
    
    # Ngôn ngữ phản hồi mong muốn
    response_language = models.CharField(max_length=10, choices=[
        ('vi', 'Tiếng Việt'),
        ('en', 'Tiếng Anh'),
        ('ja', 'Tiếng Nhật'),
    ], default='vi', verbose_name="Ngôn ngữ phản hồi")
    
    # TTS Configuration
    TTS_ENGINE_CHOICES = [
        ('local', 'System TTS (Offline - Siêu nhẹ)'),
        ('custom', 'Custom TTS API (Tùy chỉnh)'),
    ]
    tts_engine = models.CharField(
        max_length=20,
        choices=TTS_ENGINE_CHOICES,
        default='local',
        verbose_name="Text-to-Speech Engine"
    )
    tts_custom_url = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name="Custom TTS API URL",
        help_text="Ví dụ: http://localhost:5000/tts"
    )
    
    TTS_VOICE_CHOICES = [
        ('vi', 'Tiếng Việt'),
        ('en', 'Tiếng Anh'),
        ('ja', 'Tiếng Nhật'),
    ]
    tts_voice = models.CharField(
        max_length=10, 
        choices=TTS_VOICE_CHOICES, 
        default='vi', 
        verbose_name="Ngôn ngữ đọc"
    )
    tts_speed = models.FloatField(default=1.0, verbose_name="Tốc độ đọc")
    
    # Custom STT Server Configuration (legacy)
    custom_stt_port = models.IntegerField(default=8000, verbose_name="Port STT Server (Legacy)")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Configuration"
        verbose_name_plural = "AI Configurations"
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.name} ({'Default' if self.is_default else 'Custom'})"
    
    def save(self, *args, **kwargs):
        # Chỉ có 1 cấu hình mặc định cho mỗi user
        if self.is_default:
            AIConfiguration.objects.filter(
                user=self.user, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class MCPTool(models.Model):
    """Model cho MCP Tools - Dynamic tool registry"""
    TOOL_TYPE_CHOICES = [
        ('builtin', 'Built-in Tool'),
        ('external_api', 'External API'),
        ('database', 'Database Query'),
        ('custom_handler', 'Custom Handler'),
    ]
    
    name = models.CharField(max_length=100, unique=True, verbose_name="Tool ID")
    display_name = models.CharField(max_length=200, verbose_name="Tên hiển thị")
    description = models.TextField(verbose_name="Mô tả")
    tool_type = models.CharField(max_length=20, choices=TOOL_TYPE_CHOICES, default='builtin', verbose_name="Loại tool")
    
    # Connection to MCP Server
    server = models.ForeignKey(MCPServer, on_delete=models.CASCADE, null=True, blank=True, related_name='tools')
    mcp_schema = models.JSONField(default=dict, blank=True, verbose_name="MCP Schema", help_text="Full JSON schema for the tool (params, descriptions)")
    
    # Module và function để import (cho built-in tools)
    module_path = models.CharField(max_length=255, blank=True, verbose_name="Module path")
    function_name = models.CharField(max_length=100, blank=True, verbose_name="Function name")
    
    # External API config (cho external tools)
    api_endpoint = models.URLField(blank=True, null=True, verbose_name="API Endpoint")
    api_method = models.CharField(max_length=10, default='GET', choices=[('GET', 'GET'), ('POST', 'POST')], verbose_name="HTTP Method")
    api_headers = models.JSONField(default=dict, blank=True, verbose_name="API Headers")
    
    # Keywords cho routing
    keywords = models.JSONField(default=list, verbose_name="Keywords", help_text="List of keywords for smart routing")
    
    # UI Config
    icon = models.CharField(max_length=50, default='fa-terminal', verbose_name="Icon class")
    color_class = models.CharField(max_length=50, default='border-info text-info', verbose_name="CSS color class")
    category = models.CharField(max_length=50, default='General', verbose_name="Category")
    quick_command = models.CharField(max_length=200, blank=True, verbose_name="Quick command example")
    
    # Status
    is_enabled = models.BooleanField(default=True, verbose_name="Đang bật")
    is_visible = models.BooleanField(default=True, verbose_name="Hiển thị trên UI")
    is_public = models.BooleanField(default=True, verbose_name="Công khai (Cho phép User tự thêm)")
    is_system = models.BooleanField(default=False, verbose_name="Hệ thống (Mặc định cho mọi User)")
    priority = models.IntegerField(default=0, verbose_name="Priority", help_text="Higher = checked first in routing")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "MCP Tool"
        verbose_name_plural = "MCP Tools"
        ordering = ['-priority', 'category', 'name']
    
    def __str__(self):
        return f"{self.display_name} ({self.name})"
    
    @property
    def keywords_list(self):
        """Return keywords as list"""
        if isinstance(self.keywords, list):
            return self.keywords
        return []
    
    def to_dict(self):
        """Convert to dict for API response"""
        return {
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'tool_type': self.tool_type,
            'keywords': self.keywords_list,
            'icon': self.icon,
            'color_class': self.color_class,
            'category': self.category,
            'quick_command': self.quick_command,
            'is_enabled': self.is_enabled,
            'is_visible': self.is_visible,
        }


class UserMCPTool(models.Model):
    """Quan hệ user - tool (user chỉ dùng được tools đã được gán)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='mcp_tools')
    tool = models.ForeignKey(MCPTool, on_delete=models.CASCADE, related_name='user_assignments')
    is_active = models.BooleanField(default=True, verbose_name="Đang kích hoạt")
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "User MCP Tool"
        verbose_name_plural = "User MCP Tools"
        unique_together = ['user', 'tool']
        ordering = ['-added_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.tool.display_name}"

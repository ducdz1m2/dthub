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
        ('public', 'Public Server'),
        ('local', 'Local Server (Auto-scanned)')
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

class STTConfiguration(models.Model):
    """Cấu hình Speech-to-Text riêng biệt"""
    name = models.CharField(max_length=100, verbose_name="Tên cấu hình STT")
    
    ENGINE_CHOICES = [
        ('whisper', 'Faster-Whisper (Local)'),
        ('custom', 'Custom STT API (Tùy chỉnh)'),
    ]
    engine = models.CharField(
        max_length=20, 
        choices=ENGINE_CHOICES, 
        default='whisper', 
        verbose_name="Speech-to-Text Engine"
    )
    
    LANGUAGE_CHOICES = [
        ('vi-VN', 'Tiếng Việt'),
        ('en-US', 'Tiếng Anh'),
        ('ja-JP', 'Tiếng Nhật'),
        ('ko-KR', 'Tiếng Hàn'),
        ('zh-CN', 'Tiếng Trung'),
    ]
    language = models.CharField(
        max_length=10, 
        choices=LANGUAGE_CHOICES, 
        default='vi-VN', 
        verbose_name="Ngôn ngữ nhận diện"
    )
    
    custom_url = models.CharField(
        max_length=255, 
        blank=True, null=True, 
        verbose_name="Custom STT API URL",
        help_text="Ví dụ: http://localhost:5000/stt"
    )
    
    # Cấu hình nâng cao
    model_size = models.CharField(
        max_length=20,
        choices=[
            ('tiny', 'Tiny (Nhanh nhất)'),
            ('base', 'Base (Cân bằng)'),
            ('small', 'Small (Chính xác)'),
            ('medium', 'Medium (Rất chính xác)'),
        ],
        default='base',
        verbose_name="Kích thước model"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Hoạt động")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "STT Configuration"
        verbose_name_plural = "STT Configurations"
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        return f"STT: {self.name} ({self.get_engine_display()})"


class LLMConfiguration(models.Model):
    """Cấu hình Language Model riêng biệt - Qwen2.5 Series"""
    name = models.CharField(max_length=100, verbose_name="Tên cấu hình LLM")
    
    MODEL_CHOICES = [
        ('qwen2.5:0.5b', 'Qwen2.5 0.5B (Siêu nhẹ - Nhanh nhất)'),
        ('qwen2.5:1.5b', 'Qwen2.5 1.5B (Nhẹ - Cân bằng)'),
        ('qwen2.5:3b', 'Qwen2.5 3B (Thông minh)'),
        ('qwen2.5:7b', 'Qwen2.5 7B (Cao cấp)'),
        ('qwen2.5:14b', 'Qwen2.5 14B (Chuyên nghiệp)'),
    ]
    model = models.CharField(
        max_length=50, 
        choices=MODEL_CHOICES, 
        default='qwen2.5:1.5b', 
        verbose_name="Model AI (Qwen2.5 Series)"
    )
    
    temperature = models.FloatField(
        default=0.1, 
        verbose_name="Độ sáng tạo (0-2)",
        help_text="0: Rất bảo thủ, 2: Rất sáng tạo"
    )
    
    max_tokens = models.IntegerField(
        default=1024, 
        verbose_name="Độ dài trả lời tối đa",
        help_text="Số token tối đa trong một phản hồi"
    )
    
    LANGUAGE_CHOICES = [
        ('vi', 'Tiếng Việt'),
        ('en', 'Tiếng Anh'),
        ('ja', 'Tiếng Nhật'),
        ('ko', 'Tiếng Hàn'),
        ('zh', 'Tiếng Trung'),
    ]
    response_language = models.CharField(
        max_length=10, 
        choices=LANGUAGE_CHOICES, 
        default='vi', 
        verbose_name="Ngôn ngữ phản hồi"
    )
    
    # System prompt cho từng ngôn ngữ
    system_prompt = models.TextField(
        blank=True,
        verbose_name="System Prompt",
        help_text="Hướng dẫn cho AI về cách phản hồi"
    )

    router_model = models.CharField(
        max_length=50,
        default='qwen2.5:0.5b',
        verbose_name="Model Router",
        help_text="Model nhỏ/nhanh dùng cho AI Router để phân tích intent",
    )

    router_timeout = models.IntegerField(
        default=3,
        verbose_name="Router Timeout (giây)",
        help_text="Thời gian tối đa chờ AI Router phản hồi trước khi fallback",
    )

    is_active = models.BooleanField(default=True, verbose_name="Hoạt động")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "LLM Configuration"
        verbose_name_plural = "LLM Configurations"
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        return f"LLM: {self.name} ({self.model})"
    
    def save(self, *args, **kwargs):
        if not self.system_prompt:
            # Set default system prompt based on language
            default_prompts = {
                'vi': 'Bạn là một trợ lý AI thông minh và hữu ích. Hãy trả lời bằng Tiếng Việt một cách tự nhiên và thân thiện.',
                'en': 'You are an intelligent and helpful AI assistant. Please respond in English naturally and friendly.',
                'ja': 'あなたは知的で有用なAIアシスタントです。日本語で自然に、親切に回答してください。',
                'ko': '당신은 지능적이고 유용한 AI 어시스턴트입니다. 한국어로 자연스럽고 친절하게 답변해주세요.',
                'zh': '你是一个智能且有用的AI助手。请用中文自然友好地回答。'
            }
            self.system_prompt = default_prompts.get(self.response_language, self.system_prompt)
        super().save(*args, **kwargs)


class TTSConfiguration(models.Model):
    """Cấu hình Text-to-Speech riêng biệt"""
    name = models.CharField(max_length=100, verbose_name="Tên cấu hình TTS")
    
    ENGINE_CHOICES = [
        ('piper', 'Piper TTS / sherpa-onnx (Local)'),
        ('custom', 'Custom TTS API (Tùy chỉnh)'),
    ]
    engine = models.CharField(
        max_length=20,
        choices=ENGINE_CHOICES,
        default='piper',
        verbose_name="Text-to-Speech Engine"
    )
    
    LANGUAGE_CHOICES = [
        ('vi', 'Tiếng Việt'),
        ('en', 'Tiếng Anh'),
        ('ja', 'Tiếng Nhật'),
        ('ko', 'Tiếng Hàn'),
        ('zh', 'Tiếng Trung'),
    ]
    language = models.CharField(
        max_length=10, 
        choices=LANGUAGE_CHOICES, 
        default='vi', 
        verbose_name="Ngôn ngữ đọc"
    )
    
    custom_url = models.CharField(
        max_length=255,
        blank=True, null=True,
        verbose_name="Custom TTS API URL",
        help_text="Ví dụ: http://localhost:5000/tts"
    )
    
    # Cấu hình giọng nói
    voice_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Voice ID",
        help_text="ID của giọng đọc (để trống để dùng mặc định)"
    )
    
    speed = models.FloatField(
        default=1.0, 
        verbose_name="Tốc độ đọc",
        help_text="0.5: Chậm, 1.0: Bình thường, 2.0: Nhanh"
    )
    
    pitch = models.FloatField(
        default=1.0,
        verbose_name="Tông giọng",
        help_text="0.5: Trầm, 1.0: Bình thường, 2.0: Cao"
    )
    
    volume = models.FloatField(
        default=1.0,
        verbose_name="Âm lượng",
        help_text="0.1: Yếu, 1.0: Bình thường, 2.0: To"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Hoạt động")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "TTS Configuration"
        verbose_name_plural = "TTS Configurations"
        ordering = ['-is_active', 'name']
    
    def __str__(self):
        return f"TTS: {self.name} ({self.get_engine_display()})"


class AIConfiguration(models.Model):
    """Cấu hình AI tổng hợp - kết hợp 3 phần STT, LLM, TTS"""
    name = models.CharField(max_length=100, verbose_name="Tên cấu hình AI")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        null=True, blank=True,
        help_text="Để trống cho cấu hình mặc định"
    )
    
    # Liên kết đến các cấu hình riêng biệt
    stt_config = models.ForeignKey(
        STTConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Cấu hình STT"
    )
    
    llm_config = models.ForeignKey(
        LLMConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Cấu hình LLM"
    )
    
    tts_config = models.ForeignKey(
        TTSConfiguration,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name="Cấu hình TTS"
    )
    
    is_default = models.BooleanField(default=False, verbose_name="Mặc định")
    is_active = models.BooleanField(default=True, verbose_name="Hoạt động")
    
    description = models.TextField(
        blank=True,
        verbose_name="Mô tả",
        help_text="Mô tả về cấu hình AI này"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "AI Configuration"
        verbose_name_plural = "AI Configurations"
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"AI: {self.name} ({'Default' if self.is_default else 'Custom'})"
    
    def save(self, *args, **kwargs):
        # Chỉ có 1 cấu hình mặc định cho mỗi user
        if self.is_default:
            AIConfiguration.objects.filter(
                user=self.user, 
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    def get_active_configs(self):
        """Lấy các cấu hình đang hoạt động"""
        return {
            'stt': self.stt_config if self.stt_config and self.stt_config.is_active else None,
            'llm': self.llm_config if self.llm_config and self.llm_config.is_active else None,
            'tts': self.tts_config if self.tts_config and self.tts_config.is_active else None,
        }


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
    
    # Connection to MCP Server (legacy — kept for compatibility)
    server = models.ForeignKey(MCPServer, on_delete=models.CASCADE, null=True, blank=True, related_name='tools')

    # Server thực sự cung cấp tool này (NULL = tool nội bộ/ảo, không nên hiện cho user)
    source_server = models.ForeignKey(
        MCPServer,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='discovered_tools',
        verbose_name='Nguồn server',
        help_text='Server thực sự cung cấp tool này. Null = tool nội bộ (ảo).',
    )
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


class UserDocument(models.Model):
    """Tài liệu người dùng upload để dùng với RAG."""
    STATUS_CHOICES = [
        ('pending', 'Đang xử lý'),
        ('success', 'Thành công'),
        ('failed', 'Thất bại'),
    ]
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    filename = models.CharField(max_length=255, verbose_name="Tên file")
    file = models.FileField(
        upload_to='rag_documents/%Y/%m/',
        null=True, blank=True,
        verbose_name="File gốc",
    )
    file_type = models.CharField(max_length=10, verbose_name="Loại file")
    file_size = models.IntegerField(verbose_name="Kích thước (bytes)")
    chunk_count = models.IntegerField(default=0, verbose_name="Số chunks")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='pending', verbose_name="Trạng thái"
    )
    error_message = models.TextField(blank=True, verbose_name="Lỗi")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Document"
        verbose_name_plural = "User Documents"
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.user.username} — {self.filename} ({self.status})"


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


class KnowledgeBase(models.Model):
    """Bộ tri thức RAG — admin tạo, user có thể thêm vào chat của mình."""
    name = models.CharField(max_length=200, verbose_name="Tên bộ tri thức")
    description = models.TextField(verbose_name="Mô tả")
    namespace = models.CharField(max_length=100, unique=True, verbose_name="RAG Namespace",
                                  help_text="Namespace trong RAG service (vd: kb_history, kb_physics)")
    icon = models.CharField(max_length=50, default='fa-book', verbose_name="Icon class")
    color_class = models.CharField(max_length=50, default='border-info text-info', verbose_name="CSS color class")
    category = models.CharField(max_length=50, default='General', verbose_name="Danh mục")
    is_public = models.BooleanField(default=True, verbose_name="Công khai (User có thể thêm)")
    is_system = models.BooleanField(default=False, verbose_name="Hệ thống (Tự động áp dụng cho mọi user)")
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    verbose_name="Tạo bởi")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Knowledge Base"
        verbose_name_plural = "Knowledge Bases"
        ordering = ['-is_system', 'category', 'name']

    def __str__(self):
        return f"{self.name} [{self.namespace}]"


class UserKnowledgeBase(models.Model):
    """Quan hệ user - knowledge base."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='knowledge_bases')
    kb = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='user_assignments')
    is_active = models.BooleanField(default=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "User Knowledge Base"
        verbose_name_plural = "User Knowledge Bases"
        unique_together = ['user', 'kb']
        ordering = ['-added_at']

    def __str__(self):
        return f"{self.user.username} - {self.kb.name}"

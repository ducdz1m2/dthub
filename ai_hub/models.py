from django.db import models
from django.conf import settings

class AIConfig(models.Model):
    name = models.CharField(max_length=255)
    endpoint = models.URLField()

    class Meta:
        permissions = [
            ("manage_ai_architecture", "Can manage AI architecture"),
        ]

class ESP32Device(models.Model):
    """Model cho ESP32 devices"""
    device_id = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    device_type = models.CharField(max_length=50, choices=[
        ('sensor', 'Sensor Node'),
        ('actuator', 'Actuator Node'),
        ('hybrid', 'Sensor + Actuator')
    ])
    mqtt_topic = models.CharField(max_length=200)
    location = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.name} ({self.device_id})"

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

class ChatSession(models.Model):
    """Model cho chat sessions với AI"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Session {self.session_id} - {self.user.username}"

class ChatMessage(models.Model):
    """Model cho chat messages"""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE)
    query = models.TextField()
    response = models.TextField()
    tool_used = models.CharField(max_length=50)
    confidence = models.FloatField()
    response_time = models.FloatField(help_text="Response time in seconds")
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['timestamp']
    
    def __str__(self):
        return f"{self.session.session_id} - {self.tool_used}"

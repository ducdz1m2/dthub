from django import forms
from .models import ESP32Device, MCPServer, AIConfiguration, STTConfiguration, LLMConfiguration, TTSConfiguration, DeviceControlLabel

class DeviceControlLabelForm(forms.ModelForm):
    class Meta:
        model = DeviceControlLabel
        fields = ['channel', 'label', 'is_active']
        widgets = {
            'channel': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: relay1, relay2, gpio2'}),
            'label': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Quạt trần, Đèn ngủ'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'channel': 'Mã kênh (Channel ID)',
            'label': 'Tên nhãn (Label)',
            'is_active': 'Kích hoạt',
        }

class MCPServerForm(forms.ModelForm):
    class Meta:
        model = MCPServer
        fields = ['name', 'device_id', 'domain', 'description', 'location', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: My Local MCP'}),
            'device_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: local-mcp-01'}),
            'domain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'http://localhost:8001 hoặc mcp.example.com'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Tên Server',
            'device_id': 'Device ID (Duy nhất)',
            'domain': 'URL của MCP Server',
            'description': 'Mô tả',
            'location': 'Vị trí',
            'is_active': 'Kích hoạt',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
    
    def clean_device_id(self):
        device_id = self.cleaned_data['device_id']
        if MCPServer.objects.filter(device_id=device_id).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("Device ID này đã tồn tại!")
        return device_id

class STTConfigurationForm(forms.ModelForm):
    """Form cho STT Configuration"""
    
    class Meta:
        model = STTConfiguration
        fields = ['name', 'engine', 'language', 'model_size', 'custom_url', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: STT Tiếng Việt'}),
            'engine': forms.Select(attrs={'class': 'form-select', 'id': 'id_stt_engine'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'model_size': forms.Select(attrs={'class': 'form-select'}),
            'custom_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'http://localhost:5000/stt'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Tên cấu hình STT',
            'engine': 'Engine STT',
            'language': 'Ngôn ngữ nhận diện',
            'model_size': 'Kích thước model',
            'custom_url': 'Custom API URL',
            'is_active': 'Hoạt động',
        }


class LLMConfigurationForm(forms.ModelForm):
    """Form cho LLM Configuration"""
    
    class Meta:
        model = LLMConfiguration
        fields = ['name', 'model', 'temperature', 'max_tokens', 'response_language', 'system_prompt', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: LLM Qwen2.5 1.5B'}),
            'model': forms.Select(attrs={'class': 'form-select'}),
            'temperature': forms.NumberInput(attrs={
                'class': 'form-range', 
                'type': 'range', 
                'min': '0', 
                'max': '2', 
                'step': '0.1',
                'oninput': 'this.nextElementSibling.value = this.value'
            }),
            'max_tokens': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 4096}),
            'response_language': forms.Select(attrs={'class': 'form-select'}),
            'system_prompt': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'router_model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: qwen2.5:0.5b'}),
            'router_timeout': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 30}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Tên cấu hình LLM',
            'model': 'Model AI (Qwen2.5)',
            'temperature': 'Độ sáng tạo',
            'max_tokens': 'Token tối đa',
            'response_language': 'Ngôn ngữ phản hồi',
            'system_prompt': 'System Prompt',
            'router_model': 'Model Router (AI Router)',
            'router_timeout': 'Router Timeout (giây)',
            'is_active': 'Hoạt động',
        }


class TTSConfigurationForm(forms.ModelForm):
    """Form cho TTS Configuration"""
    
    class Meta:
        model = TTSConfiguration
        fields = ['name', 'engine', 'language', 'voice_id', 'speed', 'pitch', 'volume', 'custom_url', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: TTS Tiếng Việt'}),
            'engine': forms.Select(attrs={'class': 'form-select', 'id': 'id_tts_engine'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'voice_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Để trống dùng mặc định'}),
            'speed': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0.5', 'max': '2.0'}),
            'pitch': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0.5', 'max': '2.0'}),
            'volume': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0.1', 'max': '2.0'}),
            'custom_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'http://localhost:5000/tts'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'name': 'Tên cấu hình TTS',
            'engine': 'Engine TTS',
            'language': 'Ngôn ngữ đọc',
            'voice_id': 'Voice ID',
            'speed': 'Tốc độ đọc',
            'pitch': 'Tông giọng',
            'volume': 'Âm lượng',
            'custom_url': 'Custom API URL',
            'is_active': 'Hoạt động',
        }


class AIConfigurationForm(forms.ModelForm):
    """Form cho AI Configuration tổng hợp"""
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Lọc các cấu hình đang hoạt động
        if user and not user.is_superuser:
            # User thường chỉ thấy các config của mình và config mặc định
            self.fields['stt_config'].queryset = STTConfiguration.objects.filter(
                is_active=True
            )
            self.fields['llm_config'].queryset = LLMConfiguration.objects.filter(
                is_active=True
            )
            self.fields['tts_config'].queryset = TTSConfiguration.objects.filter(
                is_active=True
            )
        else:
            # Superuser thấy tất cả
            self.fields['stt_config'].queryset = STTConfiguration.objects.filter(
                is_active=True
            )
            self.fields['llm_config'].queryset = LLMConfiguration.objects.filter(
                is_active=True
            )
            self.fields['tts_config'].queryset = TTSConfiguration.objects.filter(
                is_active=True
            )
    
    class Meta:
        model = AIConfiguration
        fields = ['name', 'stt_config', 'llm_config', 'tts_config', 'is_default', 'is_active', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Cấu hình AI Tiếng Việt'}),
            'stt_config': forms.Select(attrs={'class': 'form-select'}),
            'llm_config': forms.Select(attrs={'class': 'form-select'}),
            'tts_config': forms.Select(attrs={'class': 'form-select'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Mô tả về cấu hình AI này...'}),
        }
        labels = {
            'name': 'Tên cấu hình AI',
            'stt_config': 'Cấu hình STT',
            'llm_config': 'Cấu hình LLM',
            'tts_config': 'Cấu hình TTS',
            'is_default': 'Đặt làm mặc định',
            'is_active': 'Kích hoạt',
            'description': 'Mô tả',
        }

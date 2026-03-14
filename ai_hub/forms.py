from django import forms
from .models import MCPServer, AIConfiguration, DeviceControlLabel

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
    builtin_kind = forms.ChoiceField(
        required=False,
        choices=[("", "Không dùng node tích hợp")],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Node tích hợp",
    )

    class Meta:
        model = MCPServer
        fields = ['name', 'device_id', 'server_type', 'domain', 'description', 'location']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'device_id': forms.TextInput(attrs={'class': 'form-control'}),
            'server_type': forms.Select(attrs={'class': 'form-select'}),
            'domain': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'http://127.0.0.1:9101 hoặc mcp.example.com'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Tên Server',
            'device_id': 'Device ID',
            'server_type': 'Loại Server',
            'domain': 'Domain',
            'description': 'Mô tả',
            'location': 'Vị trí',
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
        from .builtin_mcp import builtin_choices
        self.fields['builtin_kind'].choices = builtin_choices(include_none=True)
        
        # Admin có thể tạo public server
        if user and user.is_superuser:
            self.fields['server_type'].choices = [
                ('private', 'Private Server'),
                ('public', 'Public Server - Global'),
            ]
        else:
            # Khách hàng chỉ tạo private server
            self.fields['server_type'].choices = [
                ('private', 'Private Server'),
            ]
    
    def clean_device_id(self):
        device_id = self.cleaned_data['device_id']
        # Kiểm tra trùng lặp
        if MCPServer.objects.filter(device_id=device_id).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise forms.ValidationError("Device ID này đã tồn tại!")
        return device_id

class AIConfigurationForm(forms.ModelForm):
    """Form để quản lý AI Configuration (đơn giản hóa)"""
    
    llm_model = forms.ChoiceField(
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Model AI (Ollama)"
    )

    class Meta:
        model = AIConfiguration
        fields = [
            'name', 'is_default', 'is_active',
            'response_language',
            'stt_engine', 'stt_language', 'stt_custom_url',
            'llm_model', 'llm_temperature', 'llm_max_tokens',
            'tts_engine', 'tts_voice', 'tts_speed', 'tts_custom_url',
            'custom_stt_port'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'VD: Cấu hình Tiếng Việt'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'response_language': forms.Select(attrs={'class': 'form-select'}),
            'stt_engine': forms.Select(attrs={'class': 'form-select', 'id': 'id_stt_engine'}),
            'stt_language': forms.Select(attrs={'class': 'form-select'}),
            'stt_custom_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'http://localhost:8000/transcribe'}),
            'llm_temperature': forms.NumberInput(attrs={
                'class': 'form-range', 
                'type': 'range', 
                'min': '0', 
                'max': '2', 
                'step': '0.1',
                'oninput': 'this.nextElementSibling.value = this.value'
            }),
            'llm_max_tokens': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 4096}),
            'tts_engine': forms.Select(attrs={'class': 'form-select', 'id': 'id_tts_engine'}),
            'tts_voice': forms.Select(attrs={'class': 'form-select'}),
            'tts_speed': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1', 'min': '0.5', 'max': '2.0'}),
            'tts_custom_url': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'http://localhost:8001/synthesize'}),
            'custom_stt_port': forms.NumberInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Tên cấu hình',
            'is_default': 'Đặt làm mặc định',
            'is_active': 'Kích hoạt',
            'response_language': 'Ngôn ngữ phản hồi (AI)',
            'stt_engine': 'STT Engine',
            'stt_language': 'Ngôn ngữ nhận dạng (STT)',
            'stt_custom_url': 'URL API STT Tùy Chỉnh',
            'llm_model': 'Model LLM (Ollama)',
            'llm_temperature': 'Độ sáng tạo (Temperature)',
            'llm_max_tokens': 'Độ dài tối đa (Tokens)',
            'tts_engine': 'TTS Engine (Local/API)',
            'tts_voice': 'Ngôn ngữ đọc (Local TTS)',
            'tts_speed': 'Tốc độ đọc',
            'tts_custom_url': 'URL API TTS Tùy Chỉnh',
            'custom_stt_port': 'Port STT (Legacy)',
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.user = user
        
        # Lấy danh sách model từ Ollama thực tế
        import ollama
        try:
            models_data = ollama.list()
            model_choices = []
            
            # Xử lý cả ListResponse object (bản mới) và dict (bản cũ)
            if hasattr(models_data, 'models'):
                # ListResponse object
                for m in models_data.models:
                    name = getattr(m, 'model', getattr(m, 'name', ''))
                    if name:
                        model_choices.append((name, name))
            elif isinstance(models_data, dict):
                # Dict response
                for m in models_data.get('models', []):
                    name = m.get('name') or m.get('model')
                    if name:
                        model_choices.append((name, name))
            
            if not model_choices:
                model_choices = [('qwen2.5:1.5b', 'qwen2.5:1.5b (Default)')]
            
            self.fields['llm_model'].choices = model_choices
        except Exception as e:
            print(f"Error fetching Ollama models: {e}")
            # Fallback nếu không kết nối được Ollama
            self.fields['llm_model'].choices = [('qwen2.5:1.5b', 'qwen2.5:1.5b (Default)')]

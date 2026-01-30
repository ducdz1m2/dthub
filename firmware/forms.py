from django import forms
from .models import FirmwareFile

class FirmwareFileForm(forms.ModelForm):
    class Meta:
        model = FirmwareFile
        fields = ['name', 'device_type', 'version', 'description', 'bin_file', 'manifest_file', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tên firmware...'
            }),
            'device_type': forms.Select(attrs={'class': 'form-select'}),
            'version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ví dụ: 1.0.0'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Mô tả chi tiết về firmware...'
            }),
            'bin_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.bin'
            }),
            'manifest_file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.json'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
        labels = {
            'name': 'Tên firmware',
            'device_type': 'Loại thiết bị',
            'version': 'Phiên bản',
            'description': 'Mô tả',
            'bin_file': 'File .bin',
            'manifest_file': 'File manifest.json (tùy chọn)',
            'is_active': 'Kích hoạt'
        }
    
    def clean_bin_file(self):
        bin_file = self.cleaned_data.get('bin_file')
        if bin_file:
            if not bin_file.name.endswith('.bin'):
                raise forms.ValidationError('File phải có định dạng .bin')
        return bin_file
    
    def clean_manifest_file(self):
        manifest_file = self.cleaned_data.get('manifest_file')
        if manifest_file:
            if not manifest_file.name.endswith('.json'):
                raise forms.ValidationError('File phải có định dạng .json')
        return manifest_file

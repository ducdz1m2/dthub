from django import forms
from .models import FirmwareFile

class FirmwareFileForm(forms.ModelForm):
    class Meta:
        model = FirmwareFile
        fields = ['name', 'device_type', 'version', 'description', 'hardware_image', 'bin_file', 'manifest_file', 'is_active']
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
            'hardware_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
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
            'hardware_image': 'Hình ảnh mạch điện',
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
    
    def clean_hardware_image(self):
        hardware_image = self.cleaned_data.get('hardware_image')
        if hardware_image:
            # Check file size (max 5MB)
            if hardware_image.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Kích thước hình ảnh không được vượt quá 5MB')
            
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_extension = hardware_image.name.lower().split('.')[-1]
            if f'.{file_extension}' not in valid_extensions:
                raise forms.ValidationError('Chỉ chấp nhận các định dạng hình ảnh: jpg, jpeg, png, gif, bmp, webp')
        return hardware_image

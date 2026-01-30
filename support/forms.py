from django import forms
from .models import SupportRequest, SupportResponse, SupportAttachment

class SupportRequestForm(forms.ModelForm):
    class Meta:
        model = SupportRequest
        fields = ['title', 'category', 'priority', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nhập tiêu đề yêu cầu hỗ trợ...'
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Mô tả chi tiết vấn đề bạn đang gặp phải...'
            })
        }
        labels = {
            'title': 'Tiêu đề',
            'category': 'Danh mục',
            'priority': 'Mức độ ưu tiên',
            'description': 'Mô tả chi tiết'
        }

class SupportResponseForm(forms.ModelForm):
    class Meta:
        model = SupportResponse
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Nhập phản hồi của bạn...'
            })
        }
        labels = {
            'content': 'Nội dung phản hồi'
        }

class SupportAttachmentForm(forms.ModelForm):
    class Meta:
        model = SupportAttachment
        fields = ['file']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': '.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif,.txt'
            })
        }
        labels = {
            'file': 'File đính kèm'
        }

SupportAttachmentFormSet = forms.inlineformset_factory(
    SupportRequest, 
    SupportAttachment, 
    form=SupportAttachmentForm,
    extra=1, 
    can_delete=True
)

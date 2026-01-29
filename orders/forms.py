from django import forms
from .models import Order, Review
class OrderForm(forms.ModelForm):
    # Khai báo đè trường address để bắt buộc nhập
    address = forms.CharField(
        label='Địa chỉ lắp đặt',
        required=True, # Bắt buộc không được để trống
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Vui lòng nhập số nhà, tên đường, phường/xã...'
        })
    )

    class Meta:
        model = Order
        fields = ['address', 'note'] 
        labels = {
            'note': 'Ghi chú cho kỹ thuật viên',
        }
        widgets = {
            'note': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3, 
                'placeholder': 'Ví dụ: Lắp ở tầng trệt, chỉ rảnh vào cuối tuần...'
            }),
        }

class ReviewForm(forms.ModelForm):
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating and (rating < 1 or rating > 5):
            raise forms.ValidationError('Rating phải nằm trong khoảng từ 1 đến 5.')
        return rating
    
    class Meta:
        model = Review
        fields = ['rating', 'comment', 'image']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Chia sẻ cảm nhận của bạn về dịch vụ...'}),
            'rating': forms.Select(attrs={'class': 'form-select'})
        }
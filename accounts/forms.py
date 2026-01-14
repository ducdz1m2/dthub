from django import forms
from .models import Profile
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone', 'avatar', 'address', 'bio']
        widgets = {
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }
        labels = {
            'phone': 'Số điện thoại',
            'avatar': 'Ảnh đại diện',
            'address': 'Địa chỉ lắp đặt/liên hệ',
            'bio': 'Tiểu sử / Kinh nghiệm kỹ thuật',
        }

User = get_user_model()
class StaffCreationForm(forms.ModelForm):
    # Bắt buộc nhập email và role
    email = forms.EmailField(required=True)
    role = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        empty_label="-- Chọn nhóm quyền --"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(),
        min_length=8,
        required=True
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email này đã được sử dụng bởi một tài khoản khác.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.is_staff = True  # Đánh dấu là nhân viên
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
            # Gán quyền vào Group
            role = self.cleaned_data.get('role')
            if role:
                user.groups.add(role)
        return user
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile

# Cách hiển thị Profile ngay trong trang chỉnh sửa User
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Thông tin chi tiết (Profile)'

# Tùy chỉnh trang quản lý User
class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )
    list_display = ('username', 'email', 'is_staff', 'get_phone') # Hiển thị thêm cột SĐT ở danh sách

    def get_phone(self, instance):
        return instance.profile.phone
    get_phone.short_description = 'Số điện thoại'

# Đăng ký vào hệ thống Admin
admin.site.register(User, CustomUserAdmin)
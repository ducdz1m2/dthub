from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.templatetags.static import static

class User(AbstractUser):
    # Chỉ còn 2 vai trò: admin (is_superuser=True) và customer (mặc định)
    is_customer = models.BooleanField(default=True)
    
    @property
    def is_admin(self):
        return self.is_superuser
    
    @property
    def role_display(self):
        if self.is_superuser:
            return "Quản trị viên"
        else:
            return "Khách hàng"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    
    # Thông tin chuyên cho nhân viên kỹ thuật
    bio = models.TextField(max_length=500, blank=True)
    current_lat = models.FloatField(blank=True, null=True)
    current_lng = models.FloatField(blank=True, null=True)

    @property
    def get_avatar_url(self):
        # Kiểm tra xem field avatar có file thực tế hay không
        if self.avatar and hasattr(self.avatar, 'url'):
            try:
                return self.avatar.url
            except ValueError:
                return static('images/avatar-default.png')
        return static('images/avatar-default.png')
    def __str__(self):
        return f"Profile of {self.user.username}"

# --- SIGNALS: Tự động tạo Profile khi tạo User ---
@receiver(post_save, sender=User)
def user_profile_handler(sender, instance, created, **kwargs):
    if created:
        Profile.objects.get_or_create(user=instance)
    else:
        Profile.objects.get_or_create(user=instance)
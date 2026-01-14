from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.templatetags.static import static

class User(AbstractUser):
    is_customer = models.BooleanField(default=True)

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
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Sử dụng hasattr để kiểm tra xem profile có tồn tại không
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # Nếu chưa có thì tạo luôn cho chắc
        Profile.objects.create(user=instance)
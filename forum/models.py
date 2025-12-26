from django.db import models

class Post(models.Model):
    author = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    content = models.TextField()

    class Meta:
        permissions = [
            ("manage_post", "Can manage forum posts"),
        ]

class Feedback(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    content = models.TextField()

    class Meta: 
        permissions = [
            ("manage_feedback", "Can manage forum feedback"),
        ]
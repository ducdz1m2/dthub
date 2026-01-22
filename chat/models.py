from django.db import models
from django.conf import settings 

class Conversation(models.Model):

    user1 = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='conv_user1'
    )
    user2 = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='conv_user2'
    )
    
    class Meta:
        unique_together = ('user1', 'user2')

class Message(models.Model):
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages'
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE
    )
    text = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta

class UserActivity(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    last_activity = models.DateTimeField(default=timezone.now)
    is_online = models.BooleanField(default=False)

    def update_activity(self):
        self.last_activity = timezone.now()
        self.is_online = True
        self.save()

    @property
    def is_active_now(self):
        # Consider user active if last activity was within last 5 minutes
        return self.is_online and (timezone.now() - self.last_activity) < timedelta(minutes=5)

    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"

class ChatMessage(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    recipient = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['sender', 'recipient', 'timestamp']),
        ]

    def clean(self):
        if not self.content.strip():
            raise ValidationError("Message content cannot be empty")
        if self.sender == self.recipient:
            raise ValidationError("Cannot send message to yourself")
        if len(self.content) > 10000:  # Reasonable limit for message length
            raise ValidationError("Message is too long")

    def save(self, *args, **kwargs):
        self.clean()
        self.content = self.content.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.sender.username} to {self.recipient.username}: {self.content[:50]}"
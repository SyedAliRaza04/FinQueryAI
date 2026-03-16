from django.db import models
from django.contrib.auth.models import User
import uuid

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Linked to Django User for data isolation
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions', null=True, blank=True)
    title = models.CharField(max_length=255, default="New Conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} ({self.owner.username if self.owner else 'No Owner'})"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    
    # Optional fields for rich components like cards or code blocks
    cards_json = models.JSONField(null=True, blank=True)
    code_snippet = models.TextField(null=True, blank=True)
    raw_data_json = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role} in {self.session.title}"

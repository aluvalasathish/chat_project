from django.contrib import admin
from .models import ChatMessage

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'content', 'timestamp', 'is_read')
    list_filter = ('sender', 'recipient', 'timestamp', 'is_read')
    search_fields = ('sender__username', 'recipient__username', 'content')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)
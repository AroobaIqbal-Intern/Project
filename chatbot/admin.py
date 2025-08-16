from django.contrib import admin
from .models import Conversation, Message, RAGQuery, PaperHighlight


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'paper', 'user', 'session_id', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['paper__title', 'user__username', 'session_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'message_type', 'timestamp', 'confidence_score']
    list_filter = ['message_type', 'timestamp']
    search_fields = ['content', 'conversation__paper__title']
    readonly_fields = ['id', 'timestamp']


@admin.register(RAGQuery)
class RAGQueryAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'query', 'processing_time', 'created_at']
    list_filter = ['created_at']
    search_fields = ['query', 'response', 'conversation__paper__title']
    readonly_fields = ['id', 'created_at']


@admin.register(PaperHighlight)
class PaperHighlightAdmin(admin.ModelAdmin):
    list_display = ['id', 'paper', 'highlight_type', 'page_number', 'created_at']
    list_filter = ['highlight_type', 'created_at', 'page_number']
    search_fields = ['text_content', 'paper__title']
    readonly_fields = ['id', 'created_at']

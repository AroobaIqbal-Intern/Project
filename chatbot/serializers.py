"""
Serializers for the chatbot app.
"""
from rest_framework import serializers
from .models import Conversation, Message, RAGQuery, PaperHighlight


class ConversationSerializer(serializers.ModelSerializer):
    """Serializer for Conversation model."""
    paper_title = serializers.CharField(source='paper.title', read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'paper', 'paper_title', 'user', 'session_id', 
            'created_at', 'updated_at', 'message_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class MessageSerializer(serializers.ModelSerializer):
    """Serializer for Message model."""
    conversation_id = serializers.UUIDField(source='conversation.id', read_only=True)
    
    class Meta:
        model = Message
        fields = [
            'id', 'conversation', 'conversation_id', 'message_type', 
            'content', 'timestamp', 'relevant_chunks', 'confidence_score', 'sources'
        ]
        read_only_fields = ['id', 'timestamp']


class RAGQuerySerializer(serializers.ModelSerializer):
    """Serializer for RAGQuery model."""
    conversation_id = serializers.UUIDField(source='conversation.id', read_only=True)
    
    class Meta:
        model = RAGQuery
        fields = [
            'id', 'conversation', 'conversation_id', 'query', 'response',
            'relevant_chunks', 'similarity_scores', 'processing_time', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class PaperHighlightSerializer(serializers.ModelSerializer):
    """Serializer for PaperHighlight model."""
    paper_title = serializers.CharField(source='paper.title', read_only=True)
    message_content = serializers.CharField(source='message.content', read_only=True)
    
    class Meta:
        model = PaperHighlight
        fields = [
            'id', 'paper', 'paper_title', 'message', 'message_content',
            'text_content', 'page_number', 'start_position', 'end_position',
            'highlight_type', 'color', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatRequestSerializer(serializers.Serializer):
    """Serializer for chat request."""
    message = serializers.CharField(max_length=2000)
    session_id = serializers.CharField(max_length=100, required=False)


class RAGQueryRequestSerializer(serializers.Serializer):
    """Serializer for RAG query request."""
    paper_id = serializers.UUIDField()
    query = serializers.CharField(max_length=2000)

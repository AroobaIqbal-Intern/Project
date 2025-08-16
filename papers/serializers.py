"""
Serializers for the papers app.
"""
from rest_framework import serializers
from .models import Paper, Reference, PaperChunk


class PaperSerializer(serializers.ModelSerializer):
    """Serializer for Paper model."""
    reference_count = serializers.ReadOnlyField()
    citation_count = serializers.ReadOnlyField()
    
    class Meta:
        model = Paper
        fields = [
            'id', 'title', 'author', 'abstract', 'file', 'uploaded_at',
            'processed', 'doi', 'journal', 'year', 'keywords',
            'reference_count', 'citation_count'
        ]
        read_only_fields = ['id', 'uploaded_at', 'processed']


class ReferenceSerializer(serializers.ModelSerializer):
    """Serializer for Reference model."""
    source_paper = PaperSerializer(read_only=True)
    target_paper = PaperSerializer(read_only=True)
    
    class Meta:
        model = Reference
        fields = ['id', 'source_paper', 'target_paper', 'reference_text', 'created_at']


class PaperChunkSerializer(serializers.ModelSerializer):
    """Serializer for PaperChunk model."""
    
    class Meta:
        model = PaperChunk
        fields = ['id', 'content', 'chunk_index', 'page_number', 'section', 'created_at']


class PaperUploadSerializer(serializers.ModelSerializer):
    """Serializer for paper upload."""
    
    class Meta:
        model = Paper
        fields = ['title', 'author', 'abstract', 'file', 'doi', 'journal', 'year', 'keywords']
    
    def validate_file(self, value):
        """Validate uploaded file."""
        if value.size > 50 * 1024 * 1024:  # 50MB limit
            raise serializers.ValidationError("File size must be less than 50MB.")
        return value


class PaperSearchSerializer(serializers.Serializer):
    """Serializer for paper search."""
    query = serializers.CharField(max_length=500)
    filters = serializers.JSONField(required=False)
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)

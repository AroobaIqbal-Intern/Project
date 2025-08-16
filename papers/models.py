"""
Models for the papers app.
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import uuid


class Paper(models.Model):
    """Model representing an academic paper."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=500)
    author = models.CharField(max_length=200)
    abstract = models.TextField(blank=True, null=True)
    file = models.FileField(
        upload_to='papers/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'docx', 'txt'])]
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    content_text = models.TextField(blank=True, null=True)
    
    # Metadata
    doi = models.CharField(max_length=100, blank=True, null=True)
    journal = models.CharField(max_length=200, blank=True, null=True)
    year = models.IntegerField(blank=True, null=True)
    keywords = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return f"{self.title} by {self.author}"
    
    @property
    def reference_count(self):
        """Return the number of references this paper has."""
        return self.references.count()
    
    @property
    def citation_count(self):
        """Return the number of papers that cite this paper."""
        return self.cited_by.count()


class Reference(models.Model):
    """Model representing a reference between papers."""
    source_paper = models.ForeignKey(
        Paper, 
        on_delete=models.CASCADE, 
        related_name='references'
    )
    target_paper = models.ForeignKey(
        Paper, 
        on_delete=models.CASCADE, 
        related_name='cited_by'
    )
    reference_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['source_paper', 'target_paper']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.source_paper.title} → {self.target_paper.title}"


class PaperChunk(models.Model):
    """Model representing chunks of paper content for RAG."""
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField()
    chunk_index = models.IntegerField()
    page_number = models.IntegerField(blank=True, null=True)
    section = models.CharField(max_length=100, blank=True, null=True)
    embedding = models.BinaryField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['paper', 'chunk_index']
        unique_together = ['paper', 'chunk_index']
    
    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.paper.title}"


class PaperMetadata(models.Model):
    """Model for storing additional paper metadata."""
    paper = models.OneToOneField(Paper, on_delete=models.CASCADE, related_name='metadata')
    total_pages = models.IntegerField(blank=True, null=True)
    language = models.CharField(max_length=10, default='en')
    file_size = models.BigIntegerField(blank=True, null=True)
    processing_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('processing', 'Processing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending'
    )
    last_processed = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Metadata for {self.paper.title}"

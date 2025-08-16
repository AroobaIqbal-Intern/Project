from django.contrib import admin
from .models import Paper, Reference, PaperChunk, PaperMetadata


@admin.register(Paper)
class PaperAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'uploaded_at', 'processed', 'reference_count', 'citation_count']
    list_filter = ['processed', 'uploaded_at', 'year']
    search_fields = ['title', 'author', 'abstract']
    readonly_fields = ['id', 'uploaded_at', 'reference_count', 'citation_count']
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'author', 'abstract', 'file')
        }),
        ('Metadata', {
            'fields': ('doi', 'journal', 'year', 'keywords')
        }),
        ('System Fields', {
            'fields': ('id', 'uploaded_by', 'uploaded_at', 'processed', 'content_text'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Reference)
class ReferenceAdmin(admin.ModelAdmin):
    list_display = ['source_paper', 'target_paper', 'created_at']
    list_filter = ['created_at']
    search_fields = ['source_paper__title', 'target_paper__title']
    readonly_fields = ['created_at']


@admin.register(PaperChunk)
class PaperChunkAdmin(admin.ModelAdmin):
    list_display = ['paper', 'chunk_index', 'page_number', 'section', 'created_at']
    list_filter = ['created_at', 'section']
    search_fields = ['paper__title', 'content']
    readonly_fields = ['created_at']


@admin.register(PaperMetadata)
class PaperMetadataAdmin(admin.ModelAdmin):
    list_display = ['paper', 'total_pages', 'language', 'processing_status', 'last_processed']
    list_filter = ['processing_status', 'language', 'last_processed']
    search_fields = ['paper__title']
    readonly_fields = ['last_processed']

"""
URLs for the chatbot app.
"""
from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # Conversation management
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<uuid:pk>/messages/', views.MessageListView.as_view(), name='message-list'),
    
    # Chat endpoints
    path('conversations/<uuid:pk>/chat/', views.ChatView.as_view(), name='chat'),
    path('cross-paper-chat/', views.CrossPaperChatView.as_view(), name='cross-paper-chat'),
    path('network-chat/<uuid:paper_id>/', views.NetworkChatView.as_view(), name='network-chat'),
    
    # Paper highlights
    path('papers/<uuid:paper_id>/highlights/', views.PaperHighlightView.as_view(), name='paper-highlights'),
    path('highlights/', views.PaperHighlightView.as_view(), name='all-highlights'),
    
    # RAG queries
    path('rag-queries/', views.RAGQueryListView.as_view(), name='rag-queries'),
    
    # Paper processing
    path('papers/<uuid:paper_id>/process-references/', views.process_paper_references, name='process-references'),
    path('papers/<uuid:paper_id>/network-stats/', views.get_paper_network_stats, name='paper-network-stats'),
    
    # Search and statistics
    path('search-papers/', views.search_papers_by_content, name='search-papers'),
    path('system-stats/', views.get_system_stats, name='system-stats'),
]

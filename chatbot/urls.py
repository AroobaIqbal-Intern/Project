"""
URL configuration for the chatbot app.
"""
from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('conversations/', views.ConversationListView.as_view(), name='conversation-list'),
    path('conversations/<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<uuid:pk>/messages/', views.MessageListView.as_view(), name='message-list'),
    path('conversations/<uuid:pk>/chat/', views.ChatView.as_view(), name='chat'),
    path('papers/<uuid:paper_id>/chat/', views.PaperChatView.as_view(), name='paper-chat'),
    path('papers/<uuid:paper_id>/highlights/', views.PaperHighlightsView.as_view(), name='paper-highlights'),
    path('rag/query/', views.RAGQueryView.as_view(), name='rag-query'),
]

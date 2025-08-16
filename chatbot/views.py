"""
API views for the chatbot app.
"""
import json
import time
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from papers.models import Paper, PaperChunk
from .models import Conversation, Message, RAGQuery, PaperHighlight
from .serializers import (
    ConversationSerializer, 
    MessageSerializer, 
    RAGQuerySerializer,
    PaperHighlightSerializer
)
from .rag_engine import RAGEngine


class ConversationListView(generics.ListCreateAPIView):
    """List and create conversations."""
    serializer_class = ConversationSerializer
    
    def get_queryset(self):
        paper_id = self.request.query_params.get('paper_id')
        if paper_id:
            return Conversation.objects.filter(paper_id=paper_id)
        return Conversation.objects.all()


class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a conversation."""
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer


class MessageListView(generics.ListCreateAPIView):
    """List and create messages for a conversation."""
    serializer_class = MessageSerializer
    
    def get_queryset(self):
        conversation_id = self.kwargs['pk']
        return Message.objects.filter(conversation_id=conversation_id)


class ChatView(generics.GenericAPIView):
    """Handle chat interactions."""
    parser_classes = [JSONParser]
    
    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        user_message = request.data.get('message', '')
        
        if not user_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=user_message
        )
        
        # Process with RAG engine
        rag_engine = RAGEngine()
        start_time = time.time()
        
        try:
            response, relevant_chunks, sources = rag_engine.query(
                user_message, 
                conversation.paper
            )
            processing_time = time.time() - start_time
            
            # Create assistant message
            assistant_msg = Message.objects.create(
                conversation=conversation,
                message_type='assistant',
                content=response,
                relevant_chunks=relevant_chunks,
                sources=sources
            )
            
            # Create RAG query record
            RAGQuery.objects.create(
                conversation=conversation,
                query=user_message,
                response=response,
                relevant_chunks=relevant_chunks,
                similarity_scores=sources,
                processing_time=processing_time
            )
            
            # Update conversation timestamp
            conversation.save()  # This triggers updated_at update
            
            return Response({
                'user_message': MessageSerializer(user_msg).data,
                'assistant_message': MessageSerializer(assistant_msg).data,
                'processing_time': processing_time
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error processing query: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PaperChatView(generics.GenericAPIView):
    """Handle chat interactions for a specific paper."""
    parser_classes = [JSONParser]
    
    def post(self, request, paper_id):
        paper = get_object_or_404(Paper, pk=paper_id)
        user_message = request.data.get('message', '')
        session_id = request.data.get('session_id', '')
        
        if not user_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Get or create conversation
        conversation, created = Conversation.objects.get_or_create(
            paper=paper,
            session_id=session_id,
            defaults={'user': request.user if request.user.is_authenticated else None}
        )
        
        # Create user message
        user_msg = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=user_message
        )
        
        # Process with RAG engine
        rag_engine = RAGEngine()
        start_time = time.time()
        
        try:
            response, relevant_chunks, sources = rag_engine.query(user_message, paper)
            processing_time = time.time() - start_time
            
            # Create assistant message
            assistant_msg = Message.objects.create(
                conversation=conversation,
                message_type='assistant',
                content=response,
                relevant_chunks=relevant_chunks,
                sources=sources
            )
            
            # Create highlights for relevant content
            self._create_highlights(paper, user_message, response, relevant_chunks)
            
            # Prepare highlighting data for frontend
            highlighting_data = self._prepare_highlighting_data(relevant_chunks)
            
            return Response({
                'conversation_id': str(conversation.id),
                'user_message': MessageSerializer(user_msg).data,
                'assistant_message': MessageSerializer(assistant_msg).data,
                'processing_time': processing_time,
                'highlights_created': True,
                'highlighting_data': highlighting_data
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error processing query: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _create_highlights(self, paper, question, answer, relevant_chunks):
        """Create highlights for relevant content in the paper."""
        try:
            # Create highlight for the question
            PaperHighlight.objects.create(
                paper=paper,
                message=Message.objects.filter(conversation__paper=paper).last(),
                text_content=question,
                highlight_type='question',
                color='#FF6B6B'
            )
            
            # Create highlight for the answer
            PaperHighlight.objects.create(
                paper=paper,
                message=Message.objects.filter(conversation__paper=paper).last(),
                text_content=answer,
                highlight_type='answer',
                color='#4ECDC4'
            )
            
            # Create highlights for relevant chunks
            for chunk_data in relevant_chunks:
                if 'content' in chunk_data:
                    PaperHighlight.objects.create(
                        paper=paper,
                        message=Message.objects.filter(conversation__paper=paper).last(),
                        text_content=chunk_data['content'][:200] + '...',
                        highlight_type='relevant',
                        color='#FFD700'
                    )
        except Exception as e:
            # Log error but don't fail the chat
            print(f"Error creating highlights: {e}")
    
    def _prepare_highlighting_data(self, relevant_chunks):
        """Prepare highlighting data for frontend."""
        highlighting_data = []
        
        for chunk in relevant_chunks:
            if 'content' in chunk:
                # Extract key phrases for highlighting
                content = chunk['content']
                phrases = self._extract_highlight_phrases(content)
                
                highlighting_data.append({
                    'chunk_id': chunk.get('id', ''),
                    'content': content,
                    'phrases': phrases,
                    'relevance_score': chunk.get('relevance_score', 0.8)
                })
        
        return highlighting_data
    
    def _extract_highlight_phrases(self, content):
        """Extract key phrases for highlighting from content."""
        import re
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', content)
        phrases = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 20:
                continue
            
            # Extract meaningful phrases (3-8 words)
            words = sentence.split()
            for i in range(len(words) - 2):
                for j in range(3, min(9, len(words) - i + 1)):
                    phrase = ' '.join(words[i:i+j])
                    if 15 < len(phrase) < 100:
                        phrases.append(phrase)
            
            # Limit phrases per sentence
            if len(phrases) >= 5:
                break
        
        # Return unique phrases, sorted by length
        return sorted(list(set(phrases)), key=len, reverse=True)[:10]


class PaperHighlightsView(generics.ListAPIView):
    """List highlights for a specific paper."""
    serializer_class = PaperHighlightSerializer
    
    def get_queryset(self):
        paper_id = self.kwargs['paper_id']
        return PaperHighlight.objects.filter(paper_id=paper_id)


class RAGQueryView(generics.GenericAPIView):
    """Direct RAG query endpoint."""
    parser_classes = [JSONParser]
    
    def post(self, request):
        paper_id = request.data.get('paper_id')
        query = request.data.get('query', '')
        
        if not paper_id or not query:
            return Response(
                {'error': 'Both paper_id and query are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        paper = get_object_or_404(Paper, pk=paper_id)
        rag_engine = RAGEngine()
        
        try:
            response, relevant_chunks, sources = rag_engine.query(query, paper)
            
            return Response({
                'query': query,
                'response': response,
                'relevant_chunks': relevant_chunks,
                'sources': sources
            })
            
        except Exception as e:
            return Response(
                {'error': f'Error processing query: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

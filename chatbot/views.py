"""
Enhanced API views for the chatbot app with cross-paper capabilities.
"""
import json
import time
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from papers.models import Paper, PaperChunk, Reference
from .models import Conversation, Message, RAGQuery, PaperHighlight
from django.db import models
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
    """Handle chat interactions with enhanced cross-paper capabilities."""
    parser_classes = [JSONParser]
    
    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk)
        user_message = request.data.get('message', '')
        query_type = request.data.get('query_type', 'single_paper')  # single_paper, cross_paper, network
        
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
            if query_type == 'cross_paper':
                # Cross-paper query across entire system
                response, relevant_chunks, sources = rag_engine.query(
                    user_message, 
                    paper=None, 
                    cross_paper=True
                )
            elif query_type == 'network':
                # Reference network query
                response, relevant_chunks, sources = rag_engine.query_reference_network(
                    user_message, 
                    conversation.paper
                )
            else:
                # Single paper query (default)
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
                'message': response,
                'relevant_chunks': relevant_chunks,
                'sources': sources,
                'processing_time': processing_time,
                'query_type': query_type
            })
            
        except Exception as e:
            return Response({
                'error': f'Error processing message: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class CrossPaperChatView(generics.GenericAPIView):
    """Handle cross-paper chat interactions without requiring a specific paper."""
    parser_classes = [JSONParser]
    
    def post(self, request):
        user_message = request.data.get('message', '')
        max_papers = request.data.get('max_papers', 10)
        
        if not user_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process with RAG engine for cross-paper search
        rag_engine = RAGEngine()
        rag_engine.max_papers = max_papers
        start_time = time.time()
        
        try:
            response, relevant_chunks, sources = rag_engine.query(
                user_message, 
                paper=None, 
                cross_paper=True
            )
            
            processing_time = time.time() - start_time
            
            return Response({
                'message': response,
                'relevant_chunks': relevant_chunks,
                'sources': sources,
                'processing_time': processing_time,
                'papers_analyzed': len(set(chunk.get('paper_title', '') for chunk in relevant_chunks))
            })
            
        except Exception as e:
            return Response({
                'error': f'Error processing cross-paper query: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class NetworkChatView(generics.GenericAPIView):
    """Handle reference network chat interactions."""
    parser_classes = [JSONParser]
    
    def post(self, request, paper_id):
        paper = get_object_or_404(Paper, pk=paper_id)
        user_message = request.data.get('message', '')
        max_depth = request.data.get('max_depth', 2)
        
        if not user_message:
            return Response({'error': 'Message is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Process with RAG engine for network search
        rag_engine = RAGEngine()
        start_time = time.time()
        
        try:
            response, relevant_chunks, sources = rag_engine.query_reference_network(
                user_message, 
                paper, 
                max_depth=max_depth
            )
            
            processing_time = time.time() - start_time
            
            # Get network statistics
            network_papers = rag_engine._get_reference_network_papers(paper, max_depth)
            
            return Response({
                'message': response,
                'relevant_chunks': relevant_chunks,
                'sources': sources,
                'processing_time': processing_time,
                'network_stats': {
                    'total_papers': len(network_papers),
                    'max_depth': max_depth,
                    'start_paper': paper.title
                }
            })
            
        except Exception as e:
            return Response({
                'error': f'Error processing network query: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PaperHighlightView(generics.ListCreateAPIView):
    """List and create paper highlights."""
    serializer_class = PaperHighlightSerializer
    
    def get_queryset(self):
        paper_id = self.kwargs.get('paper_id')
        if paper_id:
            return PaperHighlight.objects.filter(paper_id=paper_id)
        return PaperHighlight.objects.all()


class RAGQueryListView(generics.ListAPIView):
    """List RAG queries for analysis."""
    serializer_class = RAGQuerySerializer
    queryset = RAGQuery.objects.all().order_by('-created_at')


@api_view(['POST'])
def process_paper_references(request, paper_id):
    """Process references for a paper recursively."""
    try:
        paper = get_object_or_404(Paper, pk=paper_id)
        recursive = request.data.get('recursive', True)
        max_depth = request.data.get('max_depth', 3)
        
        from papers.utils import extract_references_from_paper
        
        success = extract_references_from_paper(
            str(paper_id), 
            recursive=recursive, 
            max_depth=max_depth
        )
        
        if success:
            # Get updated reference count
            reference_count = paper.references.count()
            
            return Response({
                'success': True,
                'message': f'Successfully processed references for {paper.title}',
                'reference_count': reference_count,
                'recursive': recursive,
                'max_depth': max_depth
            })
        else:
            return Response({
                'success': False,
                'message': 'Failed to process references'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_paper_network_stats(request, paper_id):
    """Get statistics about a paper's reference network."""
    try:
        paper = get_object_or_404(Paper, pk=paper_id)
        
        # Get direct references
        direct_references = paper.references.count()
        
        # Get papers that cite this paper
        citations = paper.cited_by.count()
        
        # Get network depth 1 (references of references)
        depth_1_refs = set()
        for ref in paper.references.all():
            depth_1_refs.update(ref.target_paper.references.values_list('target_paper_id', flat=True))
        
        # Get network depth 2 (citations of citations)
        depth_2_citations = set()
        for citation in paper.cited_by.all():
            depth_2_citations.update(citation.source_paper.cited_by.values_list('source_paper_id', flat=True))
        
        return Response({
            'paper_title': paper.title,
            'paper_author': paper.author,
            'direct_references': direct_references,
            'citations': citations,
            'network_depth_1_references': len(depth_1_refs),
            'network_depth_2_citations': len(depth_2_citations),
            'total_network_size': direct_references + citations + len(depth_1_refs) + len(depth_2_citations)
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def search_papers_by_content(request):
    """Search papers by content for Q&A purposes."""
    try:
        query = request.query_params.get('q', '')
        max_results = int(request.query_params.get('max_results', 10))
        
        if not query:
            return Response({'error': 'Query parameter "q" is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        from django.db.models import Q
        
        # Search in titles, abstracts, and content
        papers = Paper.objects.filter(
            Q(title__icontains=query) |
            Q(abstract__icontains=query) |
            Q(content_text__icontains=query) |
            Q(author__icontains=query)
        )[:max_results]
        
        results = []
        for paper in papers:
            # Calculate relevance score
            relevance_score = 0.0
            if query.lower() in paper.title.lower():
                relevance_score += 0.4
            if query.lower() in paper.abstract.lower():
                relevance_score += 0.3
            if query.lower() in paper.content_text.lower():
                relevance_score += 0.2
            if query.lower() in paper.author.lower():
                relevance_score += 0.1
            
            results.append({
                'id': str(paper.id),
                'title': paper.title,
                'author': paper.author,
                'year': paper.year,
                'relevance_score': relevance_score,
                'reference_count': paper.reference_count,
                'citation_count': paper.citation_count
            })
        
        # Sort by relevance score
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return Response({
            'query': query,
            'results': results,
            'total_found': len(results)
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_system_stats(request):
    """Get overall system statistics for Q&A capabilities."""
    try:
        total_papers = Paper.objects.count()
        processed_papers = Paper.objects.filter(processed=True).count()
        total_references = Reference.objects.count()
        total_conversations = Conversation.objects.count()
        total_messages = Message.objects.count()
        
        # Get papers with most references
        top_referenced = Paper.objects.annotate(
            ref_count=models.Count('references')
        ).order_by('-ref_count')[:5]
        
        # Get papers with most citations
        top_cited = Paper.objects.annotate(
            citation_count=models.Count('cited_by')
        ).order_by('-citation_count')[:5]
        
        return Response({
            'total_papers': total_papers,
            'processed_papers': processed_papers,
            'total_references': total_references,
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'processing_rate': (processed_papers / total_papers * 100) if total_papers > 0 else 0,
            'top_referenced': [
                {
                    'title': p.title,
                    'author': p.author,
                    'reference_count': p.ref_count
                } for p in top_referenced
            ],
            'top_cited': [
                {
                    'title': p.title,
                    'author': p.author,
                    'citation_count': p.citation_count
                } for p in top_cited
            ]
        })
        
    except Exception as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

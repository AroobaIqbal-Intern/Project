"""
Test the improved highlighting system.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper
from chatbot.rag_engine import RAGEngine


class Command(BaseCommand):
    help = 'Test the improved highlighting system'

    def handle(self, *args, **options):
        # Get a paper with content
        paper = Paper.objects.filter(file__isnull=False).first()
        if not paper:
            self.stdout.write('No papers with content found.')
            return
        
        self.stdout.write(f'Testing highlighting on paper: {paper.title}')
        
        # Test the RAG engine
        rag_engine = RAGEngine()
        
        # Test questions
        test_questions = [
            "What is this paper about?",
            "Who is the author?",
            "What are the main findings?",
            "What methods were used?"
        ]
        
        for question in test_questions:
            self.stdout.write(f'\nQuestion: {question}')
            try:
                response, relevant_chunks, sources = rag_engine.query(question, paper)
                self.stdout.write(f'Response: {response[:100]}...')
                self.stdout.write(f'Relevant chunks: {len(relevant_chunks)}')
                
                # Show chunk content
                for i, chunk in enumerate(relevant_chunks[:2]):  # Show first 2 chunks
                    self.stdout.write(f'  Chunk {i+1}: {chunk["content"][:100]}...')
                    
            except Exception as e:
                self.stdout.write(f'Error: {e}')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Highlighting test completed!'))

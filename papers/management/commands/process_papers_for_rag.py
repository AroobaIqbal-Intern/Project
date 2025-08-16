"""
Management command to process papers for RAG functionality.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper
from chatbot.rag_engine import RAGEngine


class Command(BaseCommand):
    help = 'Process papers for RAG (Retrieval-Augmented Generation) functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paper-id',
            type=str,
            help='Process a specific paper by ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all papers with uploaded files',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reprocessing even if already processed',
        )

    def handle(self, *args, **options):
        rag_engine = RAGEngine()
        
        if options['paper_id']:
            # Process specific paper
            try:
                paper = Paper.objects.get(id=options['paper_id'])
                self.process_paper(paper, rag_engine, options['force'])
            except Paper.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Paper with ID {options["paper_id"]} not found')
                )
        elif options['all']:
            # Process all papers with files
            papers = Paper.objects.exclude(file='')
            self.stdout.write(f'Processing {papers.count()} papers...')
            
            for paper in papers:
                self.process_paper(paper, rag_engine, options['force'])
        else:
            # Process papers that haven't been processed yet
            papers = Paper.objects.exclude(file='').filter(processed=False)
            self.stdout.write(f'Processing {papers.count()} unprocessed papers...')
            
            for paper in papers:
                self.process_paper(paper, rag_engine, False)
    
    def process_paper(self, paper, rag_engine, force=False):
        """Process a single paper for RAG."""
        try:
            self.stdout.write(f'Processing paper: {paper.title[:50]}...')
            
            if paper.processed and not force:
                self.stdout.write(
                    self.style.WARNING(f'Paper already processed. Use --force to reprocess.')
                )
                return
            
            # Check if paper has content
            if not paper.content_text:
                self.stdout.write(
                    self.style.WARNING(f'Paper has no content text. Skipping.')
                )
                return
            
            # Process with RAG engine
            success = rag_engine.process_paper(paper)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully processed paper: {paper.title[:50]}')
                )
                self.stdout.write(f'  - Chunks created: {paper.chunks.count()}')
            else:
                self.stdout.write(
                    self.style.ERROR(f'✗ Failed to process paper: {paper.title[:50]}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Error processing paper {paper.title[:50]}: {e}')
            )


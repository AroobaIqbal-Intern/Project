"""
Management command to show the status of papers in the system.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper, Reference


class Command(BaseCommand):
    help = 'Show the status of papers in the system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed information about each paper',
        )

    def handle(self, *args, **options):
        papers = Paper.objects.all()
        total_papers = papers.count()
        
        # Count papers with files
        papers_with_files = papers.exclude(file='').count()
        
        # Count papers with content
        papers_with_content = papers.exclude(content_text__isnull=True).exclude(content_text='').count()
        
        # Count references
        total_references = Reference.objects.count()
        
        self.stdout.write(
            self.style.SUCCESS(f'\n📊 Paper System Status Report\n')
        )
        self.stdout.write(f'Total papers: {total_papers}')
        self.stdout.write(f'Papers with uploaded files: {papers_with_files}')
        self.stdout.write(f'Papers with processed content: {papers_with_content}')
        self.stdout.write(f'Total references: {total_references}')
        
        # Calculate percentages
        if total_papers > 0:
            file_percentage = (papers_with_files / total_papers) * 100
            content_percentage = (papers_with_content / total_papers) * 100
            
            self.stdout.write(f'\n📈 Statistics:')
            self.stdout.write(f'Papers with files: {file_percentage:.1f}%')
            self.stdout.write(f'Papers with content: {content_percentage:.1f}%')
        
        if options['detailed']:
            self.stdout.write(f'\n📋 Detailed Paper List:')
            for paper in papers:
                status = []
                if paper.file:
                    status.append('📄 Has file')
                if paper.content_text and paper.content_text.strip():
                    status.append('📝 Has content')
                if paper.references.exists():
                    status.append(f'🔗 References: {paper.references.count()}')
                if paper.cited_by.exists():
                    status.append(f'📚 Cited by: {paper.cited_by.count()}')
                
                status_str = ', '.join(status) if status else '❌ No content'
                
                self.stdout.write(
                    f'\n• {paper.title[:60]}{"..." if len(paper.title) > 60 else ""}'
                )
                self.stdout.write(f'  Author: {paper.author}')
                self.stdout.write(f'  Status: {status_str}')
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Status report completed!')
        )

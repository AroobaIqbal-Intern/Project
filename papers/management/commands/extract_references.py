"""
Management command to extract references from papers.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper
from papers.utils import extract_references_from_paper


class Command(BaseCommand):
    help = 'Extract references from papers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paper-id',
            type=str,
            help='Extract references from a specific paper by ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Extract references from all papers',
        )

    def handle(self, *args, **options):
        if options['paper_id']:
            # Process specific paper
            try:
                paper = Paper.objects.get(id=options['paper_id'])
                self.stdout.write(f'Processing paper: {paper.title}')
                success = extract_references_from_paper(str(paper.id))
                if success:
                    self.stdout.write(self.style.SUCCESS('✓ Reference extraction completed'))
                else:
                    self.stdout.write(self.style.ERROR('✗ Reference extraction failed'))
            except Paper.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Paper with ID {options["paper_id"]} not found')
                )
        elif options['all']:
            # Process all papers
            papers = Paper.objects.all()
            self.stdout.write(f'Processing {papers.count()} papers...')
            
            for paper in papers:
                self.stdout.write(f'\nProcessing: {paper.title[:50]}...')
                success = extract_references_from_paper(str(paper.id))
                if success:
                    self.stdout.write(self.style.SUCCESS('  ✓ Completed'))
                else:
                    self.stdout.write(self.style.ERROR('  ✗ Failed'))
        else:
            # Process papers without references
            papers = Paper.objects.filter(references__isnull=True)
            self.stdout.write(f'Processing {papers.count()} papers without references...')
            
            for paper in papers:
                self.stdout.write(f'\nProcessing: {paper.title[:50]}...')
                success = extract_references_from_paper(str(paper.id))
                if success:
                    self.stdout.write(self.style.SUCCESS('  ✓ Completed'))
                else:
                    self.stdout.write(self.style.ERROR('  ✗ Failed'))

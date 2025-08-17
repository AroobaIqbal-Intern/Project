"""
Management command to process references recursively for all papers.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from papers.models import Paper
from papers.utils import extract_references_from_paper
import time
from django.db import models


class Command(BaseCommand):
    help = 'Process references recursively for all papers to build a complete knowledge graph'

    def add_arguments(self, parser):
        parser.add_argument(
            '--paper-id',
            type=str,
            help='Process references for a specific paper ID',
        )
        parser.add_argument(
            '--max-depth',
            type=int,
            default=3,
            help='Maximum depth for recursive reference extraction (default: 3)',
        )
        parser.add_argument(
            '--recursive',
            action='store_true',
            default=True,
            help='Enable recursive processing (default: True)',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=10,
            help='Number of papers to process in each batch (default: 10)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually processing',
        )

    def handle(self, *args, **options):
        paper_id = options['paper_id']
        max_depth = options['max_depth']
        recursive = options['recursive']
        batch_size = options['batch_size']
        dry_run = options['dry_run']

        self.stdout.write(
            self.style.SUCCESS(
                f'Starting recursive reference processing with max_depth={max_depth}, recursive={recursive}'
            )
        )

        if paper_id:
            # Process specific paper
            try:
                paper = Paper.objects.get(id=paper_id)
                self.process_single_paper(paper, max_depth, recursive, dry_run)
            except Paper.DoesNotExist:
                raise CommandError(f'Paper with ID {paper_id} does not exist')
        else:
            # Process all papers
            self.process_all_papers(max_depth, recursive, batch_size, dry_run)

    def process_single_paper(self, paper, max_depth, recursive, dry_run):
        """Process references for a single paper."""
        self.stdout.write(f'Processing paper: {paper.title}')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would process references for "{paper.title}" '
                    f'(depth={max_depth}, recursive={recursive})'
                )
            )
            return

        start_time = time.time()
        
        try:
            success = extract_references_from_paper(
                str(paper.id), 
                recursive=recursive, 
                max_depth=max_depth
            )
            
            processing_time = time.time() - start_time
            
            if success:
                reference_count = paper.references.count()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'✓ Successfully processed "{paper.title}" '
                        f'({reference_count} references, {processing_time:.2f}s)'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        f'✗ Failed to process "{paper.title}"'
                    )
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f'✗ Error processing "{paper.title}": {str(e)}'
                )
            )

    def process_all_papers(self, max_depth, recursive, batch_size, dry_run):
        """Process references for all papers in batches."""
        # Get papers that need processing
        papers = Paper.objects.filter(processed=True).order_by('-uploaded_at')
        total_papers = papers.count()
        
        if total_papers == 0:
            self.stdout.write(
                self.style.WARNING('No processed papers found to extract references from.')
            )
            return

        self.stdout.write(f'Found {total_papers} papers to process')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'[DRY RUN] Would process {total_papers} papers '
                    f'(depth={max_depth}, recursive={recursive}, batch_size={batch_size})'
                )
            )
            return

        # Process in batches
        processed_count = 0
        success_count = 0
        error_count = 0
        
        for i in range(0, total_papers, batch_size):
            batch = papers[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_papers + batch_size - 1) // batch_size
            
            self.stdout.write(
                f'\nProcessing batch {batch_num}/{total_batches} '
                f'({len(batch)} papers)...'
            )
            
            for paper in batch:
                try:
                    start_time = time.time()
                    
                    success = extract_references_from_paper(
                        str(paper.id), 
                        recursive=recursive, 
                        max_depth=max_depth
                    )
                    
                    processing_time = time.time() - start_time
                    processed_count += 1
                    
                    if success:
                        reference_count = paper.references.count()
                        success_count += 1
                        self.stdout.write(
                            f'  ✓ {paper.title[:50]}... ({reference_count} refs, {processing_time:.2f}s)'
                        )
                    else:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ {paper.title[:50]}... (failed)')
                        )
                        
                except Exception as e:
                    error_count += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ {paper.title[:50]}... (error: {str(e)})')
                    )
                
                # Progress update
                if processed_count % 5 == 0:
                    progress = (processed_count / total_papers) * 100
                    self.stdout.write(
                        f'  Progress: {processed_count}/{total_papers} ({progress:.1f}%)'
                    )

        # Final summary
        self.stdout.write('\n' + '='*50)
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing complete!\n'
                f'Total papers: {total_papers}\n'
                f'Successful: {success_count}\n'
                f'Errors: {error_count}\n'
                f'Success rate: {(success_count/total_papers)*100:.1f}%'
            )
        )

        # Show system statistics
        self.show_system_stats()

    def show_system_stats(self):
        """Show system statistics after processing."""
        total_papers = Paper.objects.count()
        total_references = sum(paper.references.count() for paper in Paper.objects.all())
        papers_with_refs = Paper.objects.filter(references__isnull=False).distinct().count()
        
        self.stdout.write('\nSystem Statistics:')
        self.stdout.write(f'  Total papers: {total_papers}')
        self.stdout.write(f'  Papers with references: {papers_with_refs}')
        self.stdout.write(f'  Total reference relationships: {total_references}')
        
        if total_papers > 0:
            coverage = (papers_with_refs / total_papers) * 100
            self.stdout.write(f'  Reference coverage: {coverage:.1f}%')
        
        # Show top papers by reference count
        top_papers = Paper.objects.annotate(
            ref_count=models.Count('references')
        ).filter(ref_count__gt=0).order_by('-ref_count')[:5]
        
        if top_papers:
            self.stdout.write('\nTop papers by reference count:')
            for paper in top_papers:
                self.stdout.write(f'  {paper.title[:40]}... ({paper.ref_count} refs)')
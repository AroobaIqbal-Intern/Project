"""
Test citation detection on paper content.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper
import re


class Command(BaseCommand):
    help = 'Test citation detection on paper content'

    def handle(self, *args, **options):
        # Get the paper with content
        paper = Paper.objects.filter(file__isnull=False).first()
        if not paper:
            self.stdout.write('No papers with content found.')
            return
        
        self.stdout.write(f'Testing paper: {paper.title}')
        self.stdout.write(f'Content length: {len(paper.content_text)}')
        
        # Test different citation patterns
        patterns = [
            r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)',
            r'([A-Z][a-z]+,\s*[A-Z]\.)\s*\((\d{4})\)',
            r'([A-Z][a-z]+(?:\s+et\s+al\.)?),\s*(\d{4})',
        ]
        
        for i, pattern in enumerate(patterns):
            self.stdout.write(f'\nPattern {i+1}: {pattern}')
            matches = re.finditer(pattern, paper.content_text, re.IGNORECASE)
            count = 0
            for match in matches:
                count += 1
                if count <= 3:  # Show first 3 matches
                    self.stdout.write(f'  Match: {match.group(0)}')
            self.stdout.write(f'  Total matches: {count}')
        
        # Look for any text that might be citations
        self.stdout.write('\nLooking for potential citation-like text...')
        lines = paper.content_text.split('\n')
        for line in lines:
            if re.search(r'\(19\d{2}|\(20\d{2}\)', line):
                self.stdout.write(f'  Potential citation line: {line.strip()[:100]}...')

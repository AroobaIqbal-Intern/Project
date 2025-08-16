"""
Create a test paper with citations to demonstrate the reference system.
"""
from django.core.management.base import BaseCommand
from papers.models import Paper, Reference


class Command(BaseCommand):
    help = 'Create a test paper with citations to demonstrate the reference system'

    def handle(self, *args, **options):
        # Create a test paper with citations
        test_content = """
        This is a test paper about machine learning in education.
        
        Recent studies have shown that machine learning can improve student outcomes.
        Smith et al. (2023) demonstrated that AI-powered tutoring systems can increase
        learning efficiency by 25%. Additionally, Johnson, A. (2022) found that
        personalized learning algorithms lead to better retention rates.
        
        The work by Brown, M. and Davis, R. (2021) established the foundation
        for adaptive learning systems. Wilson et al. (2020) further developed
        these concepts in their comprehensive review.
        
        References:
        Smith, J. et al. (2023) "AI Tutoring Systems in Education"
        Johnson, A. (2022) "Personalized Learning Algorithms"
        Brown, M. and Davis, R. (2021) "Foundations of Adaptive Learning"
        Wilson, P. et al. (2020) "Comprehensive Review of ML in Education"
        """
        
        # Create the main test paper
        test_paper, created = Paper.objects.get_or_create(
            title="Machine Learning Applications in Education: A Comprehensive Review",
            author="Test Author",
            defaults={
                'abstract': 'A review of machine learning applications in educational settings.',
                'content_text': test_content,
                'year': 2024,
                'processed': True
            }
        )
        
        if created:
            self.stdout.write(f'Created test paper: {test_paper.title}')
        else:
            self.stdout.write(f'Test paper already exists: {test_paper.title}')
        
        # Create referenced papers
        referenced_papers = [
            {
                'title': 'AI Tutoring Systems in Education',
                'author': 'Smith, J. et al.',
                'year': 2023,
                'abstract': 'Study on AI-powered tutoring systems'
            },
            {
                'title': 'Personalized Learning Algorithms',
                'author': 'Johnson, A.',
                'year': 2022,
                'abstract': 'Research on personalized learning approaches'
            },
            {
                'title': 'Foundations of Adaptive Learning',
                'author': 'Brown, M. and Davis, R.',
                'year': 2021,
                'abstract': 'Fundamental concepts in adaptive learning'
            },
            {
                'title': 'Comprehensive Review of ML in Education',
                'author': 'Wilson, P. et al.',
                'year': 2020,
                'abstract': 'Systematic review of machine learning in education'
            }
        ]
        
        created_refs = []
        for ref_data in referenced_papers:
            ref_paper, created = Paper.objects.get_or_create(
                title=ref_data['title'],
                author=ref_data['author'],
                defaults={
                    'abstract': ref_data['abstract'],
                    'year': ref_data['year'],
                    'processed': False
                }
            )
            
            if created:
                self.stdout.write(f'  Created referenced paper: {ref_paper.title}')
            else:
                self.stdout.write(f'  Referenced paper already exists: {ref_paper.title}')
            
            created_refs.append(ref_paper)
        
        # Create reference relationships
        for ref_paper in created_refs:
            ref_obj, created = Reference.objects.get_or_create(
                source_paper=test_paper,
                target_paper=ref_paper,
                defaults={'reference_text': f'Cited in {test_paper.title}'}
            )
            if created:
                self.stdout.write(f'  Created reference: {test_paper.title} -> {ref_paper.title}')
        
        self.stdout.write(self.style.SUCCESS('\n✓ Test paper with references created successfully!'))
        self.stdout.write(f'Main paper: {test_paper.title}')
        self.stdout.write(f'References created: {len(created_refs)}')
        
        # Now test reference extraction
        self.stdout.write('\nTesting reference extraction...')
        from papers.utils import extract_references_from_paper
        success = extract_references_from_paper(str(test_paper.id))
        
        if success:
            test_paper.refresh_from_db()
            self.stdout.write(f'Reference extraction completed. Paper now has {test_paper.references.count()} references.')
        else:
            self.stdout.write('Reference extraction failed.')

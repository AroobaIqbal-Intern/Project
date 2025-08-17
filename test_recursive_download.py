#!/usr/bin/env python3
"""
Test script for recursive paper download functionality.
"""
import os
import sys
import django

# Add the project directory to Python path
sys.path.append('/workspace')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reference_graph.settings')
django.setup()

from papers.models import Paper, Reference
from papers.paper_downloader import recursive_extractor, paper_downloader

def test_recursive_download():
    """Test the recursive paper download functionality."""
    print("Testing recursive paper download functionality...")
    
    # Get the first paper with content
    papers_with_content = Paper.objects.filter(content_text__isnull=False).exclude(content_text='')
    
    if not papers_with_content.exists():
        print("No papers with content found. Please upload a paper first.")
        return
    
    test_paper = papers_with_content.first()
    print(f"Testing with paper: {test_paper.title}")
    
    # Test single paper download
    print("\n1. Testing single paper download...")
    success = paper_downloader.download_paper(test_paper)
    if success:
        print(f"✓ Successfully downloaded paper: {test_paper.title}")
    else:
        print(f"✗ Could not download paper: {test_paper.title}")
    
    # Test recursive reference extraction
    print("\n2. Testing recursive reference extraction...")
    try:
        downloaded_papers = recursive_extractor.process_uploaded_paper(test_paper)
        print(f"✓ Recursive extraction completed. Downloaded {len(downloaded_papers)} papers.")
        
        for i, paper in enumerate(downloaded_papers, 1):
            print(f"  {i}. {paper.title} by {paper.author}")
            print(f"     Has file: {bool(paper.file)}")
            print(f"     Has content: {bool(paper.content_text)}")
            print(f"     Processed: {paper.processed}")
            print(f"     References: {paper.references.count()}")
    except Exception as e:
        print(f"✗ Error in recursive extraction: {e}")
    
    # Test reference network
    print("\n3. Testing reference network...")
    all_papers = Paper.objects.all()
    papers_with_files = all_papers.filter(file__isnull=False).exclude(file='')
    papers_with_content = all_papers.filter(content_text__isnull=False).exclude(content_text='')
    
    print(f"Total papers: {all_papers.count()}")
    print(f"Papers with files: {papers_with_files.count()}")
    print(f"Papers with content: {papers_with_content.count()}")
    
    # Show reference relationships
    print("\n4. Reference relationships:")
    for paper in all_papers[:5]:  # Show first 5 papers
        ref_count = paper.references.count()
        citation_count = paper.cited_by.count()
        print(f"  {paper.title[:50]}...")
        print(f"    References: {ref_count}, Citations: {citation_count}")

def test_download_methods():
    """Test individual download methods."""
    print("\nTesting individual download methods...")
    
    # Create a test paper
    test_paper = Paper.objects.create(
        title="Attention Is All You Need",
        author="Vaswani, A.",
        year=2017
    )
    
    print(f"Testing download for: {test_paper.title}")
    
    # Test arXiv download
    print("Testing arXiv download...")
    success = paper_downloader._download_from_arxiv(test_paper)
    print(f"arXiv download: {'✓ Success' if success else '✗ Failed'}")
    
    # Test Semantic Scholar download
    print("Testing Semantic Scholar download...")
    success = paper_downloader._download_from_semantic_scholar(test_paper)
    print(f"Semantic Scholar download: {'✓ Success' if success else '✗ Failed'}")
    
    # Clean up test paper
    test_paper.delete()

if __name__ == "__main__":
    test_recursive_download()
    test_download_methods()
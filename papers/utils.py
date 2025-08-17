"""
Utility functions for the papers app.
"""
import re
import json
import requests
from typing import List, Dict, Optional
from django.conf import settings
from .models import Paper, Reference, PaperMetadata
from chatbot.rag_engine import RAGEngine
from django.db import models


def extract_references_from_paper(paper_id: str) -> bool:
    """Extract references from a paper and create reference relationships."""
    try:
        paper = Paper.objects.get(id=paper_id)
        print(f"Processing paper: {paper.title[:50]}...")
        
        # Extract text content if not already done
        if not paper.content_text:
            print("  - Extracting text content...")
            rag_engine = RAGEngine()
            rag_engine.process_paper(paper)
        
        # Extract references from text
        references = _extract_references_from_text(paper.content_text)
        print(f"  - Found {len(references)} potential references")
        
        # Create or find referenced papers
        created_count = 0
        for ref_data in references:
            referenced_paper = _find_or_create_referenced_paper(ref_data)
            if referenced_paper:
                # Create reference relationship
                ref_obj, created = Reference.objects.get_or_create(
                    source_paper=paper,
                    target_paper=referenced_paper,
                    defaults={'reference_text': ref_data.get('text', '')}
                )
                if created:
                    created_count += 1
        
        print(f"  - Created {created_count} reference relationships")
        
        # Update paper metadata
        _update_paper_metadata(paper)
        
        return True
        
    except Exception as e:
        print(f"Error extracting references from paper {paper_id}: {e}")
        return False


def _extract_references_from_text(text: str) -> List[Dict]:
    """Extract reference information from paper text with improved patterns."""
    references = []
    
    # Improved reference patterns
    patterns = [
        # Pattern 1: Author et al. (Year) Title
        r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)\s*([^.!?]+[.!?])',
        
        # Pattern 2: Author, A. (Year) Title
        r'([A-Z][a-z]+,\s*[A-Z]\.)\s*\((\d{4})\)\s*([^.!?]+[.!?])',
        
        # Pattern 3: Author, A. and Author, B. (Year) Title
        r'([A-Z][a-z]+,\s*[A-Z]\.\s+and\s+[A-Z][a-z]+,\s*[A-Z]\.)\s*\((\d{4})\)\s*([^.!?]+[.!?])',
        
        # Pattern 4: Author et al. (Year). Title
        r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)\.\s*([^.!?]+[.!?])',
        
        # Pattern 5: Author et al., Year - comma format
        r'([A-Z][a-z]+(?:\s+et\s+al\.)?),\s*(\d{4})\s*([^.!?]+[.!?])',
        
        # Pattern 6: Author (Year) - simple format
        r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)',
        
        # Pattern 7: Author, A. B. (Year) - initials
        r'([A-Z][a-z]+,\s*[A-Z]\.[\sA-Z\.]*)\s*\((\d{4})\)\s*([^.!?]+[.!?])',
        
        # Pattern 8: Author & Author (Year) - ampersand format
        r'([A-Z][a-z]+(?:\s+&\s+[A-Z][a-z]+)*)\s*\((\d{4})\)\s*([^.!?]+[.!?])',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                author = match.group(1).strip()
                year = match.group(2).strip()
                title = match.group(3).strip() if len(match.groups()) > 2 else ""
                
                # Basic validation
                if (len(author) > 3 and 
                    year.isdigit() and 
                    len(year) == 4 and 
                    1900 < int(year) < 2030 and
                    len(title) > 10 and  # Ensure title has meaningful content
                    not title.lower() in ['correction', 'pages', 'figure', 'table', 'appendix']):  # Skip common non-paper references
                    
                    references.append({
                        'author': author,
                        'year': int(year),
                        'title': title,
                        'text': match.group(0)
                    })
            except (IndexError, ValueError):
                # Skip malformed matches
                continue
    
    # Remove duplicates based on author and year
    unique_refs = []
    seen = set()
    for ref in references:
        key = (ref['author'].lower(), ref['year'])
        if key not in seen:
            seen.add(key)
            unique_refs.append(ref)
    
    return unique_refs


def _find_or_create_referenced_paper(ref_data: Dict) -> Optional[Paper]:
    """Find or create a referenced paper."""
    try:
        # Try to find existing paper with better matching
        # First try exact title match
        existing_paper = Paper.objects.filter(
            title__iexact=ref_data['title']
        ).first()
        
        if existing_paper:
            return existing_paper
        
        # Try partial title match with author
        existing_paper = Paper.objects.filter(
            title__icontains=ref_data['title'][:100],  # Use first 100 chars for matching
            author__icontains=ref_data['author'][:50]   # Use first 50 chars for matching
        ).first()
        
        if existing_paper:
            return existing_paper
        
        # Try author and year match
        existing_paper = Paper.objects.filter(
            author__icontains=ref_data['author'][:50],
            year=ref_data['year']
        ).first()
        
        if existing_paper:
            return existing_paper
        
        # Try to find paper using external APIs (e.g., arXiv, CrossRef)
        external_paper = _search_external_paper(ref_data)
        if external_paper:
            return external_paper
        
        # Create placeholder paper if not found
        # Store reference text as content for display purposes
        content_text = f"""Reference Information:
{ref_data['text']}

Paper Details:
- Title: {ref_data['title']}
- Author: {ref_data['author']}
- Year: {ref_data['year']}

This paper was referenced in the paper "{paper.title}" by {paper.author}. The full content is not available as the original document was not uploaded to the system.

To view the complete paper, you would need to:
- Upload the actual PDF or document file using the "Upload This Paper" button above
- Or find the paper through external sources like arXiv, ResearchGate, or the publisher's website

You can also use the chatbot to ask questions about this reference and its relationship to the main paper."""
        
        return Paper.objects.create(
            title=ref_data['title'][:500],  # Limit title length
            author=ref_data['author'][:200],  # Limit author length
            year=ref_data['year'],
            content_text=content_text,
            processed=True  # Mark as processed since we have content
        )
        
    except Exception as e:
        print(f"Error finding/creating referenced paper: {e}")
        return None


def _search_external_paper(ref_data: Dict) -> Optional[Paper]:
    """Search for paper using external APIs."""
    try:
        # Try CrossRef API
        crossref_url = "https://api.crossref.org/works"
        params = {
            'query': f"{ref_data['title']} {ref_data['author']}",
            'rows': 1
        }
        
        response = requests.get(crossref_url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('message', {}).get('items'):
                item = data['message']['items'][0]
                
                # Extract information
                title = item.get('title', [''])[0] if item.get('title') else ref_data['title']
                authors = item.get('author', [])
                author = ', '.join([f"{a.get('given', '')} {a.get('family', '')}".strip() 
                                  for a in authors]) if authors else ref_data['author']
                year = item.get('published-print', {}).get('date-parts', [[None]])[0][0] or ref_data['year']
                doi = item.get('DOI', '')
                journal = item.get('container-title', [''])[0] if item.get('container-title') else ''
                
                # Create paper with content from external source
                content_text = f"Title: {title}\nAuthor: {author}\nYear: {year}\nJournal: {journal}\nDOI: {doi}\n\nThis paper was found through external search. The full content is not available as the original document was not uploaded to the system.\n\nTo view the complete paper, you would need to:\n- Upload the actual PDF or document file\n- Or access it through the DOI: {doi if doi else 'Not available'}"
                
                return Paper.objects.create(
                    title=title[:500],
                    author=author[:200],
                    year=year,
                    doi=doi,
                    journal=journal,
                    content_text=content_text,
                    processed=True
                )
        
        # Try arXiv API
        arxiv_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f"ti:{ref_data['title']}",
            'max_results': 1
        }
        
        response = requests.get(arxiv_url, params=params, timeout=10)
        if response.status_code == 200:
            # Parse arXiv XML response (simplified)
            if 'entry' in response.text:
                # Extract basic info from XML
                title_match = re.search(r'<title>(.*?)</title>', response.text)
                author_match = re.search(r'<name>(.*?)</name>', response.text)
                
                if title_match and author_match:
                    title = title_match.group(1).strip()
                    author = author_match.group(1).strip()
                    
                    content_text = f"Title: {title}\nAuthor: {author}\nYear: {ref_data['year']}\nSource: arXiv\n\nThis paper was found through arXiv search. The full content is not available as the original document was not uploaded to the system.\n\nTo view the complete paper, you would need to:\n- Upload the actual PDF or document file\n- Or access it through arXiv"
                    
                    return Paper.objects.create(
                        title=title[:500],
                        author=author[:200],
                        year=ref_data['year'],
                        content_text=content_text,
                        processed=True
                    )
        
        return None
        
    except Exception as e:
        print(f"Error searching external APIs: {e}")
        return None


def _update_paper_metadata(paper: Paper) -> None:
    """Update paper metadata after processing."""
    try:
        metadata, created = PaperMetadata.objects.get_or_create(paper=paper)
        
        # Update processing status
        metadata.processing_status = 'completed'
        metadata.save()
        
        # Update paper year if not set
        if not paper.year:
            # Try to extract year from title or content
            year_match = re.search(r'\b(19|20)\d{2}\b', paper.title)
            if year_match:
                paper.year = int(year_match.group(0))
                paper.save()
        
    except Exception as e:
        print(f"Error updating paper metadata: {e}")


def build_reference_graph(paper: Paper, max_depth: int = 3) -> Dict:
    """Build a reference graph starting from a given paper."""
    def _build_graph_recursive(current_paper: Paper, depth: int, visited: set) -> Dict:
        if depth > max_depth or str(current_paper.id) in visited:
            return None
        
        visited.add(str(current_paper.id))
        
        node = {
            'id': str(current_paper.id),
            'title': current_paper.title,
            'author': current_paper.author,
            'year': current_paper.year,
            'depth': depth
        }
        
        # Get references
        references = []
        for ref in current_paper.references.all():
            ref_node = _build_graph_recursive(ref.target_paper, depth + 1, visited)
            if ref_node:
                references.append(ref_node)
        
        node['references'] = references
        return node
    
    visited = set()
    return _build_graph_recursive(paper, 0, visited)


def get_paper_statistics() -> Dict:
    """Get statistics about papers and references."""
    try:
        total_papers = Paper.objects.count()
        processed_papers = Paper.objects.filter(processed=True).count()
        total_references = Reference.objects.count()
        
        # Papers with most references
        top_referenced = Paper.objects.annotate(
            ref_count=models.Count('references')
        ).order_by('-ref_count')[:10]
        
        # Papers with most citations
        top_cited = Paper.objects.annotate(
            citation_count=models.Count('cited_by')
        ).order_by('-citation_count')[:10]
        
        return {
            'total_papers': total_papers,
            'processed_papers': processed_papers,
            'total_references': total_references,
            'top_referenced': [
                {'title': p.title, 'author': p.author, 'count': p.ref_count}
                for p in top_referenced
            ],
            'top_cited': [
                {'title': p.title, 'author': p.author, 'count': p.citation_count}
                for p in top_cited
            ]
        }
        
    except Exception as e:
        print(f"Error getting paper statistics: {e}")
        return {}


def search_papers_by_reference(query: str) -> List[Paper]:
    """Search papers by their reference content."""
    try:
        # Search in reference text
        references = Reference.objects.filter(
            reference_text__icontains=query
        )
        
        # Get unique papers
        papers = set()
        for ref in references:
            papers.add(ref.source_paper)
            papers.add(ref.target_paper)
        
        return list(papers)
        
    except Exception as e:
        print(f"Error searching papers by reference: {e}")
        return []

"""
Utility functions for the papers app.
"""
import re
import json
import requests
from typing import List, Dict, Optional, Set
from django.conf import settings
from .models import Paper, Reference, PaperMetadata
from chatbot.rag_engine import RAGEngine
from django.db import models
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import threading


def extract_references_from_paper(paper_id: str, recursive: bool = True, max_depth: int = 3) -> bool:
    """Extract references from a paper and create reference relationships recursively."""
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
        referenced_papers = []
        
        for ref_data in references:
            referenced_paper = _find_or_create_referenced_paper(ref_data, paper)
            if referenced_paper:
                # Create reference relationship
                ref_obj, created = Reference.objects.get_or_create(
                    source_paper=paper,
                    target_paper=referenced_paper,
                    defaults={'reference_text': ref_data.get('text', '')}
                )
                if created:
                    created_count += 1
                    referenced_papers.append(referenced_paper)
        
        print(f"  - Created {created_count} reference relationships")
        
        # Update paper metadata
        _update_paper_metadata(paper)
        
        # Recursive processing if enabled
        if recursive and max_depth > 0:
            print(f"  - Starting recursive processing (depth {max_depth})...")
            _process_references_recursively(referenced_papers, max_depth - 1)
        
        return True
        
    except Exception as e:
        print(f"Error extracting references from paper {paper_id}: {e}")
        return False


def _process_references_recursively(papers: List[Paper], max_depth: int) -> None:
    """Process references recursively to build a complete knowledge graph."""
    if max_depth <= 0:
        return
    
    print(f"    Processing {len(papers)} papers at depth {max_depth}")
    
    for paper in papers:
        try:
            # Skip if already processed with references
            if paper.references.exists():
                print(f"      Skipping {paper.title[:30]}... (already has references)")
                continue
            
            # Extract references from this paper
            extract_references_from_paper(str(paper.id), recursive=True, max_depth=max_depth)
            
        except Exception as e:
            print(f"      Error processing {paper.title[:30]}: {e}")
            continue


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
        
        # Pattern 9: Enhanced bibliography format
        r'(\d+)\.\s*([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)\s*([^.!?]+[.!?])',
        
        # Pattern 10: Journal format with volume
        r'([A-Z][a-z]+(?:\s+et\s+al\.)?)\s*\((\d{4})\)\s*([^.!?]+[.!?])\s*[A-Z][a-z]+\s*\d+',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                # Handle different group structures
                groups = match.groups()
                if len(groups) >= 3:
                    # Standard format: author, year, title
                    author = groups[0].strip()
                    year = groups[1].strip()
                    title = groups[2].strip()
                elif len(groups) == 2:
                    # Simple format: author, year
                    author = groups[0].strip()
                    year = groups[1].strip()
                    title = ""
                else:
                    continue
                
                # Basic validation
                if (len(author) > 3 and 
                    year.isdigit() and 
                    len(year) == 4 and 
                    1900 < int(year) < 2030 and
                    len(title) > 10 and  # Ensure title has meaningful content
                    not title.lower() in ['correction', 'pages', 'figure', 'table', 'appendix', 'supplementary']):  # Skip common non-paper references
                    
                    references.append({
                        'author': author,
                        'year': int(year),
                        'title': title,
                        'text': match.group(0),
                        'context': _extract_reference_context(text, match.start(), match.end())
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


def _extract_reference_context(text: str, start: int, end: int, context_size: int = 200) -> str:
    """Extract context around a reference for better understanding."""
    context_start = max(0, start - context_size)
    context_end = min(len(text), end + context_size)
    
    context = text[context_start:context_end]
    
    # Clean up context
    context = re.sub(r'\s+', ' ', context).strip()
    
    return context


def _find_or_create_referenced_paper(ref_data: Dict, source_paper: Paper = None) -> Optional[Paper]:
    """Find or create a referenced paper with enhanced content storage."""
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
        external_paper = _search_external_paper_enhanced(ref_data)
        if external_paper:
            return external_paper
        
        # Create placeholder paper if not found
        # Store reference text as content for display purposes
        source_info = f"Referenced in: {source_paper.title} by {source_paper.author}" if source_paper else "Extracted from paper content"
        
        content_text = f"""Reference Information:
{ref_data['text']}

Paper Details:
- Title: {ref_data['title']}
- Author: {ref_data['author']}
- Year: {ref_data['year']}

Context:
{ref_data.get('context', 'No context available')}

Source: {source_info}

This paper was referenced in the academic literature. The full content is not available as the original document was not uploaded to the system.

To view the complete paper, you would need to:
- Upload the actual PDF or document file using the "Upload This Paper" button above
- Or find the paper through external sources like arXiv, ResearchGate, or the publisher's website

You can also use the chatbot to ask questions about this reference and its relationship to other papers in the system.

Reference Network:
- This paper may be referenced by other papers in the system
- Use the chatbot to explore connections and relationships
- Ask about methodology, findings, or how this paper relates to others"""
        
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


def _search_external_paper_enhanced(ref_data: Dict) -> Optional[Paper]:
    """Search for paper using external APIs with enhanced content retrieval."""
    try:
        # Try CrossRef API with better search
        crossref_url = "https://api.crossref.org/works"
        params = {
            'query': f"{ref_data['title']} {ref_data['author']}",
            'rows': 3,  # Get more results for better matching
            'select': 'DOI,title,author,published-print,container-title,abstract'
        }
        
        response = requests.get(crossref_url, params=params, timeout=15)
        if response.status_code == 200:
            data = response.json()
            if data.get('message', {}).get('items'):
                # Find best match
                best_match = None
                best_score = 0
                
                for item in data['message']['items']:
                    title = item.get('title', [''])[0] if item.get('title') else ''
                    authors = item.get('author', [])
                    author = ', '.join([f"{a.get('given', '')} {a.get('family', '')}".strip() 
                                      for a in authors]) if authors else ''
                    
                    # Calculate similarity score
                    title_similarity = _calculate_similarity(ref_data['title'], title)
                    author_similarity = _calculate_similarity(ref_data['author'], author)
                    score = (title_similarity * 0.7) + (author_similarity * 0.3)
                    
                    if score > best_score and score > 0.6:  # Minimum threshold
                        best_score = score
                        best_match = item
                
                if best_match:
                    # Extract information
                    title = best_match.get('title', [''])[0] if best_match.get('title') else ref_data['title']
                    authors = best_match.get('author', [])
                    author = ', '.join([f"{a.get('given', '')} {a.get('family', '')}".strip() 
                                      for a in authors]) if authors else ref_data['author']
                    year = best_match.get('published-print', {}).get('date-parts', [[None]])[0][0] or ref_data['year']
                    doi = best_match.get('DOI', '')
                    journal = best_match.get('container-title', [''])[0] if best_match.get('container-title') else ''
                    abstract = best_match.get('abstract', '')
                    
                    # Create enhanced content
                    content_text = f"""Title: {title}
Author: {author}
Year: {year}
Journal: {journal}
DOI: {doi}

Abstract:
{abstract if abstract else 'Abstract not available'}

Reference Context:
{ref_data.get('context', 'No context available')}

This paper was found through CrossRef search. The full content is not available as the original document was not uploaded to the system.

To view the complete paper, you would need to:
- Upload the actual PDF or document file
- Or access it through the DOI: {doi if doi else 'Not available'}

You can use the chatbot to ask questions about this paper and its relationships to other papers in the system."""
                    
                    return Paper.objects.create(
                        title=title[:500],
                        author=author[:200],
                        year=year,
                        doi=doi,
                        journal=journal,
                        abstract=abstract[:1000] if abstract else '',
                        content_text=content_text,
                        processed=True
                    )
        
        # Try arXiv API with enhanced search
        arxiv_url = "http://export.arxiv.org/api/query"
        params = {
            'search_query': f"ti:{ref_data['title']}",
            'max_results': 3
        }
        
        response = requests.get(arxiv_url, params=params, timeout=15)
        if response.status_code == 200:
            # Parse arXiv XML response (simplified)
            if 'entry' in response.text:
                # Extract basic info from XML
                title_match = re.search(r'<title>(.*?)</title>', response.text)
                author_match = re.search(r'<name>(.*?)</name>', response.text)
                summary_match = re.search(r'<summary>(.*?)</summary>', response.text)
                
                if title_match and author_match:
                    title = title_match.group(1).strip()
                    author = author_match.group(1).strip()
                    summary = summary_match.group(1).strip() if summary_match else ''
                    
                    content_text = f"""Title: {title}
Author: {author}
Year: {ref_data['year']}
Source: arXiv

Abstract:
{summary if summary else 'Abstract not available'}

Reference Context:
{ref_data.get('context', 'No context available')}

This paper was found through arXiv search. The full content is not available as the original document was not uploaded to the system.

To view the complete paper, you would need to:
- Upload the actual PDF or document file
- Or access it through arXiv

You can use the chatbot to ask questions about this paper and its relationships to other papers in the system."""
                    
                    return Paper.objects.create(
                        title=title[:500],
                        author=author[:200],
                        year=ref_data['year'],
                        abstract=summary[:1000] if summary else '',
                        content_text=content_text,
                        processed=True
                    )
        
        return None
        
    except Exception as e:
        print(f"Error searching external APIs: {e}")
        return None


def _calculate_similarity(str1: str, str2: str) -> float:
    """Calculate similarity between two strings."""
    if not str1 or not str2:
        return 0.0
    
    # Simple Jaccard similarity
    set1 = set(str1.lower().split())
    set2 = set(str2.lower().split())
    
    if not set1 or not set2:
        return 0.0
    
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    
    return len(intersection) / len(union) if union else 0.0


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

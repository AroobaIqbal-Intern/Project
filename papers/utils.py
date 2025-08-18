"""
Utility functions for the papers app.
"""
import os
import re
import json
import time
import urllib.parse
import requests
from typing import List, Dict, Optional
from django.conf import settings
from django.core.files.base import ContentFile
from .models import Paper, Reference, PaperMetadata
from chatbot.rag_engine import RAGEngine
from django.db import models
from bs4 import BeautifulSoup


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
                    1900 < int(year) < 2030):
                    
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
        # Try to find existing paper
        existing_paper = Paper.objects.filter(
            title__icontains=ref_data['title'][:100],  # Use first 100 chars for matching
            author__icontains=ref_data['author'][:50]   # Use first 50 chars for matching
        ).first()
        
        if existing_paper:
            return existing_paper
        
        # Try to find paper using external APIs (e.g., arXiv, CrossRef)
        external_paper = _search_external_paper(ref_data)
        if external_paper:
            return external_paper
        
        # Create placeholder paper if not found
        return Paper.objects.create(
            title=ref_data['title'][:500],  # Limit title length
            author=ref_data['author'][:200],  # Limit author length
            year=ref_data['year'],
            processed=False
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
                
                # Create paper
                return Paper.objects.create(
                    title=title[:500],
                    author=author[:200],
                    year=year,
                    doi=doi,
                    journal=journal,
                    processed=False
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
                    
                    return Paper.objects.create(
                        title=title[:500],
                        author=author[:200],
                        year=ref_data['year'],
                        processed=False
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


# ----------------------------
# Online fetching helpers
# ----------------------------

def ensure_paper_content_via_online_sources(paper_id: str) -> bool:
    """If the paper has no content/file, try to fetch an online PDF and process it.

    Returns True if content was obtained and processed; otherwise False.
    """
    try:
        paper = Paper.objects.get(id=paper_id)
    except Paper.DoesNotExist:
        return False

    # If content already exists, nothing to do
    if paper.content_text or (paper.file and paper.file.name):
        # If we have a file but not processed, process it
        if not paper.processed:
            rag = RAGEngine()
            ok = rag.process_paper(paper)
            if ok and paper.content_text:
                # Extract references once content exists
                extract_references_from_paper(str(paper.id))
            return ok
        return True

    # Try to discover and download a PDF
    downloaded = False
    # Prefer DOI if available, otherwise try to discover via CrossRef by title/author
    doi = (paper.doi or '').strip()
    if not doi:
        doi = _discover_doi_via_crossref(paper.title, paper.author, paper.year) or ''
        if doi:
            paper.doi = doi
            paper.save(update_fields=['doi'])

    if doi:
        pdf_url = _find_pdf_from_doi(doi)
        if pdf_url:
            downloaded = _download_pdf_to_paper(paper, pdf_url)

    # If still no file, try arXiv by title
    if not downloaded:
        arxiv_pdf = _find_arxiv_pdf_by_title(paper.title)
        if arxiv_pdf:
            downloaded = _download_pdf_to_paper(paper, arxiv_pdf)

    if not downloaded:
        return False

    # Process the newly downloaded file
    rag = RAGEngine()
    ok = rag.process_paper(paper)
    if ok and paper.content_text:
        extract_references_from_paper(str(paper.id))
    return ok


def _discover_doi_via_crossref(title: str, author: Optional[str], year: Optional[int]) -> Optional[str]:
    try:
        url = "https://api.crossref.org/works"
        query = title or ''
        if author:
            query += f" {author}"
        params = {"query": query, "rows": 1}
        if year:
            params["filter"] = f"from-pub-date:{year}-01-01,until-pub-date:{year}-12-31"
        r = requests.get(url, params=params, timeout=15)
        if r.status_code == 200:
            items = r.json().get('message', {}).get('items', [])
            if items:
                return items[0].get('DOI')
        return None
    except Exception:
        return None


def _find_pdf_from_doi(doi: str) -> Optional[str]:
    # Try Unpaywall first if configured
    email = os.getenv('UNPAYWALL_EMAIL') or getattr(settings, 'UNPAYWALL_EMAIL', None)
    if email:
        try:
            url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}"
            r = requests.get(url, params={"email": email}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                best = data.get('best_oa_location') or {}
                pdf_url = best.get('url_for_pdf') or best.get('url')
                if pdf_url and pdf_url.lower().endswith('.pdf'):
                    return pdf_url
        except Exception:
            pass

    # Try CrossRef 'link' entries
    try:
        cr = requests.get(f"https://api.crossref.org/works/{urllib.parse.quote(doi)}", timeout=15)
        if cr.status_code == 200:
            item = cr.json().get('message', {})
            for link in item.get('link', []) or []:
                if link.get('content-type') == 'application/pdf' and link.get('URL'):
                    return link['URL']
    except Exception:
        pass

    # Fallback: scrape DOI landing page for a PDF link
    try:
        landing = requests.get(
            f"https://doi.org/{urllib.parse.quote(doi)}",
            timeout=15,
            allow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if 200 <= landing.status_code < 400:
            pdf = _extract_pdf_url_from_html(landing.text, landing.url)
            if pdf:
                return pdf
    except Exception:
        pass

    return None


def _extract_pdf_url_from_html(html: str, base_url: str) -> Optional[str]:
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # Common meta tag used by many publishers
        meta = soup.find('meta', attrs={'name': 'citation_pdf_url'})
        if meta and meta.get('content'):
            return urllib.parse.urljoin(base_url, meta['content'])
        # Direct links ending in .pdf
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.lower().endswith('.pdf'):
                return urllib.parse.urljoin(base_url, href)
        return None
    except Exception:
        return None


def _find_arxiv_pdf_by_title(title: Optional[str]) -> Optional[str]:
    if not title:
        return None
    try:
        q = title.strip()
        url = "http://export.arxiv.org/api/query"
        r = requests.get(url, params={"search_query": f"ti:{q}", "max_results": 1}, timeout=15)
        if r.status_code == 200 and '<entry>' in r.text:
            # Extract id url and convert to pdf url
            id_match = re.search(r'<id>(.*?)</id>', r.text)
            if id_match:
                abs_url = id_match.group(1)
                if 'arxiv.org/abs/' in abs_url:
                    return abs_url.replace('/abs/', '/pdf/') + '.pdf'
        return None
    except Exception:
        return None


def _download_pdf_to_paper(paper: Paper, pdf_url: str) -> bool:
    try:
        r = requests.get(pdf_url, timeout=30, stream=True, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200:
            return False
        content_type = r.headers.get('Content-Type', '')
        if 'pdf' not in content_type and not pdf_url.lower().endswith('.pdf'):
            return False
        content = r.content
        safe_title = re.sub(r'[^a-zA-Z0-9_-]+', '_', (paper.title or 'paper'))[:50]
        filename = f"{safe_title}_{int(time.time())}.pdf"
        paper.file.save(filename, ContentFile(content), save=True)
        return True
    except Exception:
        return False

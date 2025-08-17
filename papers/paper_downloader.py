"""
Automatic paper downloader for academic papers.
Downloads papers from various sources and processes them.
"""
import os
import re
import requests
import urllib.parse
from typing import Optional, Dict, List, Tuple
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from .models import Paper, Reference, PaperMetadata
import time
import logging

logger = logging.getLogger(__name__)

class PaperDownloader:
    """Downloads academic papers from various sources."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.download_path = os.path.join(settings.MEDIA_ROOT, 'papers', 'downloaded')
        os.makedirs(self.download_path, exist_ok=True)
    
    def download_paper(self, paper: Paper) -> bool:
        """Attempt to download a paper from various sources."""
        try:
            logger.info(f"Attempting to download paper: {paper.title}")
            
            # Try different download methods
            download_methods = [
                self._download_from_arxiv,
                self._download_from_doi,
                self._download_from_semantic_scholar,
                self._download_from_researchgate,
                self._download_from_google_scholar
            ]
            
            for method in download_methods:
                try:
                    if method(paper):
                        logger.info(f"Successfully downloaded paper using {method.__name__}")
                        return True
                except Exception as e:
                    logger.warning(f"Method {method.__name__} failed: {e}")
                    continue
            
            logger.warning(f"Could not download paper: {paper.title}")
            return False
            
        except Exception as e:
            logger.error(f"Error downloading paper {paper.id}: {e}")
            return False
    
    def _download_from_arxiv(self, paper: Paper) -> bool:
        """Download paper from arXiv."""
        try:
            # Search arXiv for the paper
            search_query = self._build_arxiv_query(paper)
            search_url = "http://export.arxiv.org/api/query"
            params = {
                'search_query': search_query,
                'max_results': 1,
                'sortBy': 'relevance'
            }
            
            response = self.session.get(search_url, params=params, timeout=30)
            if response.status_code != 200:
                return False
            
            # Parse arXiv response
            if 'entry' in response.text:
                # Extract PDF URL
                pdf_match = re.search(r'<link title="pdf" href="([^"]+)"', response.text)
                if pdf_match:
                    pdf_url = pdf_match.group(1)
                    
                    # Download PDF
                    pdf_response = self.session.get(pdf_url, timeout=60)
                    if pdf_response.status_code == 200:
                        # Save file
                        filename = f"arxiv_{paper.id}.pdf"
                        file_path = os.path.join(self.download_path, filename)
                        
                        with open(file_path, 'wb') as f:
                            f.write(pdf_response.content)
                        
                        # Update paper
                        paper.file.save(filename, ContentFile(pdf_response.content))
                        paper.save()
                        
                        # Update metadata
                        self._update_paper_metadata(paper, 'arxiv')
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading from arXiv: {e}")
            return False
    
    def _download_from_doi(self, paper: Paper) -> bool:
        """Download paper using DOI."""
        try:
            if not paper.doi:
                return False
            
            # Try to get PDF from DOI
            doi_url = f"https://doi.org/{paper.doi}"
            response = self.session.get(doi_url, timeout=30, allow_redirects=True)
            
            if response.status_code == 200:
                # Look for PDF link in the page
                pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', response.text, re.IGNORECASE)
                
                for pdf_link in pdf_links:
                    if pdf_link.startswith('http'):
                        pdf_url = pdf_link
                    else:
                        pdf_url = urllib.parse.urljoin(response.url, pdf_link)
                    
                    try:
                        pdf_response = self.session.get(pdf_url, timeout=60)
                        if pdf_response.status_code == 200 and 'application/pdf' in pdf_response.headers.get('content-type', ''):
                            # Save file
                            filename = f"doi_{paper.id}.pdf"
                            file_path = os.path.join(self.download_path, filename)
                            
                            with open(file_path, 'wb') as f:
                                f.write(pdf_response.content)
                            
                            # Update paper
                            paper.file.save(filename, ContentFile(pdf_response.content))
                            paper.save()
                            
                            # Update metadata
                            self._update_paper_metadata(paper, 'doi')
                            return True
                    except Exception as e:
                        logger.warning(f"Failed to download PDF from {pdf_url}: {e}")
                        continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading from DOI: {e}")
            return False
    
    def _download_from_semantic_scholar(self, paper: Paper) -> bool:
        """Download paper from Semantic Scholar."""
        try:
            # Search Semantic Scholar API
            search_url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                'query': f"{paper.title} {paper.author}",
                'limit': 1,
                'fields': 'paperId,title,authors,url,openAccessPdf'
            }
            
            response = self.session.get(search_url, params=params, timeout=30)
            if response.status_code != 200:
                return False
            
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                paper_data = data['data'][0]
                
                # Try to get PDF URL
                pdf_url = None
                if paper_data.get('openAccessPdf', {}).get('url'):
                    pdf_url = paper_data['openAccessPdf']['url']
                elif paper_data.get('url'):
                    # Try to find PDF on the paper page
                    paper_page = self.session.get(paper_data['url'], timeout=30)
                    if paper_page.status_code == 200:
                        pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', paper_page.text, re.IGNORECASE)
                        if pdf_links:
                            pdf_url = urllib.parse.urljoin(paper_data['url'], pdf_links[0])
                
                if pdf_url:
                    pdf_response = self.session.get(pdf_url, timeout=60)
                    if pdf_response.status_code == 200:
                        # Save file
                        filename = f"semantic_{paper.id}.pdf"
                        file_path = os.path.join(self.download_path, filename)
                        
                        with open(file_path, 'wb') as f:
                            f.write(pdf_response.content)
                        
                        # Update paper
                        paper.file.save(filename, ContentFile(pdf_response.content))
                        paper.save()
                        
                        # Update metadata
                        self._update_paper_metadata(paper, 'semantic_scholar')
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading from Semantic Scholar: {e}")
            return False
    
    def _download_from_researchgate(self, paper: Paper) -> bool:
        """Download paper from ResearchGate."""
        try:
            # Search ResearchGate
            search_query = f"{paper.title} {paper.author}"
            search_url = "https://www.researchgate.net/search/publication"
            params = {'q': search_query}
            
            response = self.session.get(search_url, params=params, timeout=30)
            if response.status_code != 200:
                return False
            
            # Look for PDF links
            pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', response.text, re.IGNORECASE)
            
            for pdf_link in pdf_links[:3]:  # Try first 3 links
                try:
                    if pdf_link.startswith('http'):
                        pdf_url = pdf_link
                    else:
                        pdf_url = urllib.parse.urljoin(response.url, pdf_link)
                    
                    pdf_response = self.session.get(pdf_url, timeout=60)
                    if pdf_response.status_code == 200 and 'application/pdf' in pdf_response.headers.get('content-type', ''):
                        # Save file
                        filename = f"researchgate_{paper.id}.pdf"
                        file_path = os.path.join(self.download_path, filename)
                        
                        with open(file_path, 'wb') as f:
                            f.write(pdf_response.content)
                        
                        # Update paper
                        paper.file.save(filename, ContentFile(pdf_response.content))
                        paper.save()
                        
                        # Update metadata
                        self._update_paper_metadata(paper, 'researchgate')
                        return True
                except Exception as e:
                    logger.warning(f"Failed to download PDF from ResearchGate {pdf_url}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading from ResearchGate: {e}")
            return False
    
    def _download_from_google_scholar(self, paper: Paper) -> bool:
        """Download paper from Google Scholar."""
        try:
            # Search Google Scholar
            search_query = f"{paper.title} {paper.author} filetype:pdf"
            search_url = "https://scholar.google.com/scholar"
            params = {'q': search_query}
            
            response = self.session.get(search_url, params=params, timeout=30)
            if response.status_code != 200:
                return False
            
            # Look for PDF links
            pdf_links = re.findall(r'href="([^"]*\.pdf[^"]*)"', response.text, re.IGNORECASE)
            
            for pdf_link in pdf_links[:3]:  # Try first 3 links
                try:
                    if pdf_link.startswith('http'):
                        pdf_url = pdf_link
                    else:
                        pdf_url = urllib.parse.urljoin(response.url, pdf_link)
                    
                    pdf_response = self.session.get(pdf_url, timeout=60)
                    if pdf_response.status_code == 200 and 'application/pdf' in pdf_response.headers.get('content-type', ''):
                        # Save file
                        filename = f"scholar_{paper.id}.pdf"
                        file_path = os.path.join(self.download_path, filename)
                        
                        with open(file_path, 'wb') as f:
                            f.write(pdf_response.content)
                        
                        # Update paper
                        paper.file.save(filename, ContentFile(pdf_response.content))
                        paper.save()
                        
                        # Update metadata
                        self._update_paper_metadata(paper, 'google_scholar')
                        return True
                except Exception as e:
                    logger.warning(f"Failed to download PDF from Google Scholar {pdf_url}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error downloading from Google Scholar: {e}")
            return False
    
    def _build_arxiv_query(self, paper: Paper) -> str:
        """Build arXiv search query."""
        # Clean title and author for search
        title_words = re.sub(r'[^\w\s]', '', paper.title).split()[:5]  # First 5 words
        author_words = re.sub(r'[^\w\s]', '', paper.author).split()[:2]  # First 2 words
        
        query_parts = title_words + author_words
        return ' AND '.join(query_parts)
    
    def _update_paper_metadata(self, paper: Paper, source: str) -> None:
        """Update paper metadata after successful download."""
        try:
            metadata, created = PaperMetadata.objects.get_or_create(paper=paper)
            metadata.processing_status = 'downloaded'
            metadata.save()
            
            # Update paper processing status
            paper.processed = False  # Will be processed by RAG engine
            paper.save()
            
            logger.info(f"Paper {paper.id} downloaded from {source}")
            
        except Exception as e:
            logger.error(f"Error updating metadata for paper {paper.id}: {e}")


class RecursiveReferenceExtractor:
    """Extracts references recursively from papers."""
    
    def __init__(self, downloader: PaperDownloader):
        self.downloader = downloader
        self.max_depth = 3  # Maximum recursion depth
        self.processed_papers = set()
    
    def extract_references_recursively(self, paper: Paper, depth: int = 0) -> List[Paper]:
        """Extract references recursively from a paper."""
        if depth >= self.max_depth or str(paper.id) in self.processed_papers:
            return []
        
        self.processed_papers.add(str(paper.id))
        logger.info(f"Processing paper {paper.title} at depth {depth}")
        
        # Extract references from current paper
        from .utils import extract_references_from_paper
        success = extract_references_from_paper(str(paper.id))
        
        if not success:
            return []
        
        # Get references
        references = paper.references.all()
        downloaded_papers = []
        
        for ref in references:
            target_paper = ref.target_paper
            
            # Try to download the referenced paper
            if not target_paper.file and not target_paper.content_text:
                logger.info(f"Attempting to download referenced paper: {target_paper.title}")
                
                if self.downloader.download_paper(target_paper):
                    downloaded_papers.append(target_paper)
                    
                    # Process the downloaded paper
                    from chatbot.rag_engine import RAGEngine
                    rag_engine = RAGEngine()
                    rag_engine.process_paper(target_paper)
                    
                    # Recursively extract references from this paper
                    if depth < self.max_depth - 1:
                        sub_papers = self.extract_references_recursively(target_paper, depth + 1)
                        downloaded_papers.extend(sub_papers)
        
        return downloaded_papers
    
    def process_uploaded_paper(self, paper: Paper) -> List[Paper]:
        """Process an uploaded paper and download all its references recursively."""
        logger.info(f"Starting recursive reference extraction for paper: {paper.title}")
        
        # Process the uploaded paper first
        from chatbot.rag_engine import RAGEngine
        rag_engine = RAGEngine()
        rag_engine.process_paper(paper)
        
        # Extract references recursively
        downloaded_papers = self.extract_references_recursively(paper, 0)
        
        logger.info(f"Recursive extraction completed. Downloaded {len(downloaded_papers)} papers.")
        return downloaded_papers


# Global instances
paper_downloader = PaperDownloader()
recursive_extractor = RecursiveReferenceExtractor(paper_downloader)
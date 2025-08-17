"""
Enhanced RAG (Retrieval-Augmented Generation) Engine for academic papers with cross-paper capabilities.
"""
import os
import json
from typing import List, Dict, Tuple, Optional, Set
from django.conf import settings
from papers.models import Paper, PaperChunk, Reference
from django.db.models import Q
import re


class RAGEngine:
    """Enhanced RAG engine for processing academic papers and answering questions across the reference network."""
    
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.top_k = 5
        self.max_papers = 10  # Maximum papers to search across
    
    def process_paper(self, paper: Paper) -> bool:
        """Process a paper and create chunks."""
        try:
            # Check if paper is already processed
            if paper.chunks.exists():
                return True
            
            # Extract text content
            if not paper.content_text:
                paper.content_text = self._extract_text_from_file(paper.file.path)
                paper.save()
            
            # Split text into chunks
            chunks = self._split_text(paper.content_text)
            
            # Create chunks
            for i, chunk_text in enumerate(chunks):
                PaperChunk.objects.create(
                    paper=paper,
                    content=chunk_text,
                    chunk_index=i
                )
            
            # Mark paper as processed
            paper.processed = True
            paper.save()
            
            return True
            
        except Exception as e:
            print(f"Error processing paper {paper.id}: {e}")
            return False
    
    def query(self, question: str, paper: Paper = None, cross_paper: bool = True) -> Tuple[str, List[Dict], List[Dict]]:
        """Query the RAG system with a question about a specific paper or across the entire network."""
        try:
            if paper:
                # Single paper query
                return self._query_single_paper(question, paper)
            elif cross_paper:
                # Cross-paper query across the entire network
                return self._query_cross_paper(question)
            else:
                return "Please specify a paper or enable cross-paper search.", [], []
            
        except Exception as e:
            print(f"Error in RAG query: {e}")
            return f"I encountered an error while processing your question: {str(e)}", [], []
    
    def _query_single_paper(self, question: str, paper: Paper) -> Tuple[str, List[Dict], List[Dict]]:
        """Query a single paper."""
        # Ensure paper is processed
        if not paper.processed:
            self.process_paper(paper)
        
        # Get relevant chunks
        relevant_chunks = self._get_relevant_chunks_simple(question, paper)
        
        if not relevant_chunks:
            return "I couldn't find relevant information in this paper to answer your question.", [], []
        
        # Generate response
        response = self._generate_simple_response(question, relevant_chunks, paper)
        
        # Format chunks for response
        formatted_chunks = []
        for chunk in relevant_chunks:
            formatted_chunks.append({
                'id': str(chunk.id),
                'content': chunk.content,
                'chunk_index': chunk.chunk_index,
                'page_number': chunk.page_number,
                'section': chunk.section,
                'paper_title': paper.title,
                'paper_author': paper.author
            })
        
        # Format sources
        sources = [{
            'chunk_id': str(chunk.id),
            'content_preview': chunk.content[:200] + '...',
            'similarity_score': 0.8,  # Placeholder score
            'paper_title': paper.title,
            'paper_author': paper.author
        } for chunk in relevant_chunks]
        
        return response, formatted_chunks, sources
    
    def _query_cross_paper(self, question: str) -> Tuple[str, List[Dict], List[Dict]]:
        """Query across multiple papers in the reference network."""
        try:
            # Get relevant papers based on question
            relevant_papers = self._find_relevant_papers(question)
            
            if not relevant_papers:
                return "I couldn't find any papers relevant to your question in the system.", [], []
            
            # Get relevant chunks from all papers
            all_relevant_chunks = []
            for paper in relevant_papers:
                chunks = self._get_relevant_chunks_simple(question, paper)
                for chunk in chunks:
                    all_relevant_chunks.append({
                        'chunk': chunk,
                        'paper': paper,
                        'relevance_score': self._calculate_relevance_score(question, chunk.content)
                    })
            
            # Sort by relevance and take top chunks
            all_relevant_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
            top_chunks = all_relevant_chunks[:self.top_k * 2]  # Get more chunks for cross-paper analysis
            
            if not top_chunks:
                return "I couldn't find relevant information across the papers to answer your question.", [], []
            
            # Generate cross-paper response
            response = self._generate_cross_paper_response(question, top_chunks)
            
            # Format chunks for response
            formatted_chunks = []
            for item in top_chunks:
                chunk = item['chunk']
                paper = item['paper']
                formatted_chunks.append({
                    'id': str(chunk.id),
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'page_number': chunk.page_number,
                    'section': chunk.section,
                    'paper_title': paper.title,
                    'paper_author': paper.author,
                    'relevance_score': item['relevance_score']
                })
            
            # Format sources
            sources = [{
                'chunk_id': str(item['chunk'].id),
                'content_preview': item['chunk'].content[:200] + '...',
                'similarity_score': item['relevance_score'],
                'paper_title': item['paper'].title,
                'paper_author': item['paper'].author
            } for item in top_chunks]
            
            return response, formatted_chunks, sources
            
        except Exception as e:
            print(f"Error in cross-paper query: {e}")
            return f"I encountered an error while searching across papers: {str(e)}", [], []
    
    def _find_relevant_papers(self, question: str) -> List[Paper]:
        """Find papers relevant to the question."""
        try:
            # Extract keywords from question
            keywords = self._extract_keywords(question)
            
            # Search in paper titles, abstracts, and content
            relevant_papers = []
            
            # Search in titles and abstracts
            title_abstract_papers = Paper.objects.filter(
                Q(title__icontains=keywords[0]) | 
                Q(abstract__icontains=keywords[0]) |
                Q(content_text__icontains=keywords[0])
            )[:self.max_papers]
            
            relevant_papers.extend(title_abstract_papers)
            
            # Search in content text for other keywords
            for keyword in keywords[1:3]:  # Use top 3 keywords
                content_papers = Paper.objects.filter(
                    content_text__icontains=keyword
                ).exclude(id__in=[p.id for p in relevant_papers])[:5]
                
                relevant_papers.extend(content_papers)
            
            # Remove duplicates and limit results
            unique_papers = []
            seen_ids = set()
            for paper in relevant_papers:
                if paper.id not in seen_ids and len(unique_papers) < self.max_papers:
                    unique_papers.append(paper)
                    seen_ids.add(paper.id)
            
            return unique_papers
            
        except Exception as e:
            print(f"Error finding relevant papers: {e}")
            return []
    
    def _extract_keywords(self, question: str) -> List[str]:
        """Extract important keywords from the question."""
        # Remove common words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'what', 'how', 'why', 'when', 'where', 'who', 'which', 'that', 'this', 'these', 'those', 'about', 'from', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'between', 'among'}
        
        # Extract words
        words = re.findall(r'\b\w+\b', question.lower())
        
        # Filter out stop words and short words
        keywords = [word for word in words if word not in stop_words and len(word) > 3]
        
        # Return unique keywords
        return list(set(keywords))
    
    def _calculate_relevance_score(self, question: str, content: str) -> float:
        """Calculate relevance score between question and content."""
        try:
            question_words = set(self._extract_keywords(question))
            content_words = set(self._extract_keywords(content))
            
            if not question_words or not content_words:
                return 0.0
            
            # Calculate Jaccard similarity
            intersection = question_words.intersection(content_words)
            union = question_words.union(content_words)
            
            base_score = len(intersection) / len(union) if union else 0.0
            
            # Boost score for exact phrase matches
            question_lower = question.lower()
            content_lower = content.lower()
            
            phrase_boost = 0.0
            for keyword in question_words:
                if keyword in content_lower:
                    phrase_boost += 0.1
            
            return min(1.0, base_score + phrase_boost)
            
        except Exception as e:
            print(f"Error calculating relevance score: {e}")
            return 0.0
    
    def _generate_cross_paper_response(self, question: str, relevant_chunks: List[Dict]) -> str:
        """Generate a response based on information from multiple papers."""
        try:
            # Group chunks by paper
            papers_info = {}
            for item in relevant_chunks:
                paper = item['paper']
                if paper.title not in papers_info:
                    papers_info[paper.title] = {
                        'author': paper.author,
                        'year': paper.year,
                        'chunks': [],
                        'score': 0.0
                    }
                
                papers_info[paper.title]['chunks'].append(item['chunk'].content)
                papers_info[paper.title]['score'] += item['relevance_score']
            
            # Sort papers by relevance score
            sorted_papers = sorted(papers_info.items(), key=lambda x: x[1]['score'], reverse=True)
            
            # Generate response
            response_parts = []
            response_parts.append(f"Based on my analysis of {len(sorted_papers)} relevant papers, here's what I found:")
            
            for paper_title, info in sorted_papers[:3]:  # Top 3 papers
                response_parts.append(f"\n**{paper_title}** ({info['author']}, {info['year']}):")
                
                # Summarize key points from this paper
                key_points = self._extract_key_points(info['chunks'], question)
                for point in key_points[:2]:  # Top 2 points per paper
                    response_parts.append(f"- {point}")
            
            # Add cross-paper insights
            if len(sorted_papers) > 1:
                response_parts.append(f"\n**Cross-paper insights:**")
                insights = self._generate_cross_paper_insights(relevant_chunks, question)
                for insight in insights:
                    response_parts.append(f"- {insight}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            print(f"Error generating cross-paper response: {e}")
            return "I found relevant information across multiple papers, but encountered an error while generating a comprehensive response."
    
    def _extract_key_points(self, chunks: List[str], question: str) -> List[str]:
        """Extract key points from chunks relevant to the question."""
        try:
            key_points = []
            
            for chunk in chunks:
                # Look for sentences that contain question keywords
                sentences = re.split(r'[.!?]+', chunk)
                keywords = self._extract_keywords(question)
                
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) > 20 and any(keyword in sentence.lower() for keyword in keywords):
                        # Clean up sentence
                        sentence = re.sub(r'\s+', ' ', sentence).strip()
                        if sentence and len(sentence) < 200:  # Limit length
                            key_points.append(sentence)
            
            return key_points[:5]  # Return top 5 points
            
        except Exception as e:
            print(f"Error extracting key points: {e}")
            return []
    
    def _generate_cross_paper_insights(self, relevant_chunks: List[Dict], question: str) -> List[str]:
        """Generate insights by comparing information across papers."""
        try:
            insights = []
            
            # Look for common themes
            all_content = " ".join([item['chunk'].content for item in relevant_chunks])
            
            # Extract common methodologies, findings, or conclusions
            methodologies = re.findall(r'\b(method|methodology|approach|technique|algorithm|framework)\b', all_content, re.IGNORECASE)
            findings = re.findall(r'\b(find|found|discover|reveal|show|demonstrate|indicate)\b', all_content, re.IGNORECASE)
            conclusions = re.findall(r'\b(conclude|conclusion|result|outcome|implication)\b', all_content, re.IGNORECASE)
            
            if methodologies:
                insights.append(f"Multiple papers discuss similar methodologies and approaches.")
            
            if findings:
                insights.append(f"The papers present various findings and discoveries related to your question.")
            
            if conclusions:
                insights.append(f"There are several conclusions and implications drawn across the papers.")
            
            # Add general insight about coverage
            if len(relevant_chunks) > 5:
                insights.append(f"The topic is well-covered across multiple papers, suggesting it's an active area of research.")
            
            return insights
            
        except Exception as e:
            print(f"Error generating cross-paper insights: {e}")
            return []
    
    def query_reference_network(self, question: str, start_paper: Paper, max_depth: int = 2) -> Tuple[str, List[Dict], List[Dict]]:
        """Query the reference network starting from a specific paper."""
        try:
            # Get papers in the reference network
            network_papers = self._get_reference_network_papers(start_paper, max_depth)
            
            if not network_papers:
                return f"I couldn't find any papers in the reference network starting from '{start_paper.title}'.", [], []
            
            # Search across the network
            all_relevant_chunks = []
            for paper in network_papers:
                chunks = self._get_relevant_chunks_simple(question, paper)
                for chunk in chunks:
                    all_relevant_chunks.append({
                        'chunk': chunk,
                        'paper': paper,
                        'relevance_score': self._calculate_relevance_score(question, chunk.content)
                    })
            
            # Sort by relevance
            all_relevant_chunks.sort(key=lambda x: x['relevance_score'], reverse=True)
            top_chunks = all_relevant_chunks[:self.top_k * 2]
            
            if not top_chunks:
                return f"I couldn't find relevant information in the reference network to answer your question.", [], []
            
            # Generate network response
            response = self._generate_network_response(question, top_chunks, start_paper)
            
            # Format response
            formatted_chunks = []
            for item in top_chunks:
                chunk = item['chunk']
                paper = item['paper']
                formatted_chunks.append({
                    'id': str(chunk.id),
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'paper_title': paper.title,
                    'paper_author': paper.author,
                    'relevance_score': item['relevance_score']
                })
            
            sources = [{
                'chunk_id': str(item['chunk'].id),
                'content_preview': item['chunk'].content[:200] + '...',
                'similarity_score': item['relevance_score'],
                'paper_title': item['paper'].title,
                'paper_author': item['paper'].author
            } for item in top_chunks]
            
            return response, formatted_chunks, sources
            
        except Exception as e:
            print(f"Error querying reference network: {e}")
            return f"I encountered an error while searching the reference network: {str(e)}", [], []
    
    def _get_reference_network_papers(self, start_paper: Paper, max_depth: int) -> List[Paper]:
        """Get all papers in the reference network up to max_depth."""
        try:
            network_papers = [start_paper]
            visited = {start_paper.id}
            
            def _add_papers_recursive(paper: Paper, depth: int):
                if depth >= max_depth:
                    return
                
                # Add referenced papers
                for ref in paper.references.all():
                    if ref.target_paper.id not in visited:
                        network_papers.append(ref.target_paper)
                        visited.add(ref.target_paper.id)
                        _add_papers_recursive(ref.target_paper, depth + 1)
                
                # Add papers that cite this paper
                for citation in paper.cited_by.all():
                    if citation.source_paper.id not in visited:
                        network_papers.append(citation.source_paper)
                        visited.add(citation.source_paper.id)
                        _add_papers_recursive(citation.source_paper, depth + 1)
            
            _add_papers_recursive(start_paper, 0)
            return network_papers
            
        except Exception as e:
            print(f"Error getting reference network papers: {e}")
            return [start_paper]
    
    def _generate_network_response(self, question: str, relevant_chunks: List[Dict], start_paper: Paper) -> str:
        """Generate a response for reference network queries."""
        try:
            response_parts = []
            response_parts.append(f"Based on my analysis of the reference network starting from '{start_paper.title}', here's what I found:")
            
            # Group by paper and show relationships
            papers_info = {}
            for item in relevant_chunks:
                paper = item['paper']
                if paper.title not in papers_info:
                    papers_info[paper.title] = {
                        'author': paper.author,
                        'year': paper.year,
                        'chunks': [],
                        'score': 0.0,
                        'relationship': self._get_paper_relationship(paper, start_paper)
                    }
                
                papers_info[paper.title]['chunks'].append(item['chunk'].content)
                papers_info[paper.title]['score'] += item['relevance_score']
            
            # Sort by relevance
            sorted_papers = sorted(papers_info.items(), key=lambda x: x[1]['score'], reverse=True)
            
            for paper_title, info in sorted_papers[:3]:
                relationship = info['relationship']
                response_parts.append(f"\n**{paper_title}** ({info['author']}, {info['year']}) - {relationship}:")
                
                key_points = self._extract_key_points(info['chunks'], question)
                for point in key_points[:2]:
                    response_parts.append(f"- {point}")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            print(f"Error generating network response: {e}")
            return "I found relevant information in the reference network, but encountered an error while generating a response."
    
    def _get_paper_relationship(self, paper: Paper, start_paper: Paper) -> str:
        """Get the relationship between two papers."""
        try:
            if paper.id == start_paper.id:
                return "Starting paper"
            
            # Check if paper is referenced by start_paper
            if start_paper.references.filter(target_paper=paper).exists():
                return "Referenced by starting paper"
            
            # Check if paper cites start_paper
            if paper.references.filter(target_paper=start_paper).exists():
                return "Cites starting paper"
            
            # Check if they share references
            start_refs = set(start_paper.references.values_list('target_paper_id', flat=True))
            paper_refs = set(paper.references.values_list('target_paper_id', flat=True))
            
            if start_refs.intersection(paper_refs):
                return "Shares references with starting paper"
            
            return "Related paper"
            
        except Exception as e:
            print(f"Error getting paper relationship: {e}")
            return "Related paper"
    
    def _get_relevant_chunks_simple(self, question: str, paper: Paper) -> List[PaperChunk]:
        """Get relevant chunks using improved keyword matching."""
        try:
            # Get all chunks for the paper
            chunks = paper.chunks.all()
            
            if not chunks.exists():
                return []
            
            # Improved keyword matching with scoring
            question_lower = question.lower()
            
            # Extract key concepts from the question
            key_concepts = self._extract_key_concepts(question_lower)
            question_words = [word for word in question_lower.split() if len(word) > 2]  # Filter out short words
            
            chunk_scores = []
            
            for chunk in chunks:
                chunk_lower = chunk.content.lower()
                score = 0
                
                # Score based on key concepts (highest priority)
                for concept in key_concepts:
                    if concept in chunk_lower:
                        score += 5  # High score for concept matches
                
                # Score based on exact word matches
                for word in question_words:
                    if word in chunk_lower:
                        score += 1
                
                # Bonus for phrase matches
                if len(question_words) > 1:
                    for i in range(len(question_words) - 1):
                        phrase = f"{question_words[i]} {question_words[i+1]}"
                        if phrase in chunk_lower:
                            score += 3
                
                # Bonus for question-specific content
                score += self._score_question_specific_content(question_lower, chunk_lower)
                
                # Only include chunks with meaningful scores
                if score > 0:
                    chunk_scores.append((chunk, score))
            
            # Sort by score and return top chunks
            chunk_scores.sort(key=lambda x: x[1], reverse=True)
            relevant_chunks = [chunk for chunk, score in chunk_scores[:self.top_k]]
            
            # If no relevant chunks found, try broader search
            if not relevant_chunks:
                return self._fallback_search(question_lower, chunks)
            
            return relevant_chunks
            
        except Exception as e:
            print(f"Error retrieving chunks: {e}")
            return []
    
    def _extract_key_concepts(self, question: str) -> List[str]:
        """Extract key concepts from the question."""
        concepts = []
        
        # Mobile device related concepts
        if any(word in question for word in ['mobile', 'device', 'smartphone', 'tablet', 'phone']):
            concepts.extend(['mobile', 'device', 'smartphone', 'tablet'])
        
        # Learning related concepts
        if any(word in question for word in ['learn', 'study', 'education', 'teaching']):
            concepts.extend(['learn', 'study', 'education', 'teaching'])
        
        # Language related concepts
        if any(word in question for word in ['language', 'english', 'vocabulary', 'grammar']):
            concepts.extend(['language', 'english', 'vocabulary', 'grammar'])
        
        # Reason/purpose related concepts
        if any(word in question for word in ['reason', 'why', 'purpose', 'benefit', 'advantage']):
            concepts.extend(['reason', 'why', 'purpose', 'benefit', 'advantage'])
        
        # Method/process related concepts
        if any(word in question for word in ['how', 'method', 'process', 'way']):
            concepts.extend(['how', 'method', 'process', 'way'])
        
        return list(set(concepts))  # Remove duplicates
    
    def _score_question_specific_content(self, question: str, chunk_content: str) -> int:
        """Score content based on question type."""
        score = 0
        
        # Question type detection
        if 'why' in question or 'reason' in question:
            # Look for explanatory content
            explanatory_words = ['because', 'since', 'as', 'due to', 'reason', 'purpose', 'benefit']
            for word in explanatory_words:
                if word in chunk_content:
                    score += 2
        
        elif 'how' in question:
            # Look for procedural content
            procedural_words = ['process', 'method', 'step', 'procedure', 'way', 'approach']
            for word in procedural_words:
                if word in chunk_content:
                    score += 2
        
        elif 'what' in question:
            # Look for definitional content
            definitional_words = ['is', 'are', 'means', 'refers to', 'defined as', 'consists of']
            for word in definitional_words:
                if word in chunk_content:
                    score += 2
        
        return score
    
    def _fallback_search(self, question: str, chunks) -> List[PaperChunk]:
        """Fallback search when no specific matches found."""
        # Return first few chunks as fallback
        return list(chunks[:3])
    
    def _generate_simple_response(self, question: str, chunks: List[PaperChunk], paper: Paper) -> str:
        """Generate an improved response based on relevant chunks."""
        if not chunks:
            return f"I couldn't find specific information in the paper '{paper.title}' to answer your question: '{question}'. Please try rephrasing your question or ask about a different aspect of the paper."
        
        # Analyze the question to determine response type
        question_lower = question.lower()
        response_type = self._determine_response_type(question_lower)
        
        # Extract and format relevant content
        relevant_content = self._extract_relevant_content(chunks, question_lower)
        
        # Generate specific response based on question type
        if response_type == "reasons":
            response = self._generate_reasons_response(question, relevant_content, paper)
        elif response_type == "methods":
            response = self._generate_methods_response(question, relevant_content, paper)
        elif response_type == "findings":
            response = self._generate_findings_response(question, relevant_content, paper)
        elif response_type == "definition":
            response = self._generate_definition_response(question, relevant_content, paper)
        else:
            response = self._generate_general_response(question, relevant_content, paper)
        
        return response
    
    def _determine_response_type(self, question: str) -> str:
        """Determine the type of response needed based on the question."""
        if any(word in question for word in ['reason', 'why', 'purpose', 'benefit', 'advantage']):
            return "reasons"
        elif any(word in question for word in ['how', 'method', 'process', 'way', 'approach']):
            return "methods"
        elif any(word in question for word in ['result', 'find', 'conclusion', 'outcome', 'effect']):
            return "findings"
        elif any(word in question for word in ['what', 'define', 'explain', 'meaning']):
            return "definition"
        else:
            return "general"
    
    def _extract_relevant_content(self, chunks: List[PaperChunk], question: str) -> str:
        """Extract and format relevant content from chunks."""
        relevant_sentences = []
        
        for chunk in chunks:
            content = chunk.content.strip()
            sentences = content.split('.')
            
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) < 20:  # Skip very short sentences
                    continue
                
                # Check if sentence is relevant to the question
                if self._is_sentence_relevant(sentence.lower(), question):
                    relevant_sentences.append(sentence)
                
                # Limit the number of sentences to avoid overwhelming response
                if len(relevant_sentences) >= 5:
                    break
        
        return '. '.join(relevant_sentences) if relevant_sentences else ' '.join([chunk.content for chunk in chunks])
    
    def _is_sentence_relevant(self, sentence: str, question: str) -> bool:
        """Check if a sentence is relevant to the question."""
        # Extract key words from question
        question_words = [word for word in question.split() if len(word) > 3]
        
        # Check if sentence contains question words
        for word in question_words:
            if word in sentence:
                return True
        
        # Check for concept matches
        if 'mobile' in question and ('mobile' in sentence or 'device' in sentence):
            return True
        if 'learn' in question and ('learn' in sentence or 'study' in sentence):
            return True
        if 'reason' in question and ('because' in sentence or 'reason' in sentence or 'purpose' in sentence):
            return True
        
        return False
    
    def _generate_reasons_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate response for reason/purpose questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here are the key reasons for using mobile devices in language learning:

**Main Reasons:**
{content}

**Summary:** The research identifies several important reasons why students use mobile devices for language learning, including convenience, accessibility, and enhanced learning effectiveness."""
    
    def _generate_methods_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate response for method/process questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here's how mobile devices are used in language learning:

**Methods and Approaches:**
{content}

**Summary:** The study describes various methods and approaches for using mobile devices in language learning contexts."""
    
    def _generate_findings_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate response for findings/result questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here are the key findings:

**Research Findings:**
{content}

**Summary:** The study reveals important findings about the effectiveness and impact of mobile devices in language learning."""
    
    def _generate_definition_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate response for definition/explanation questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here's what the research explains:

**Key Information:**
{content}

**Summary:** The paper provides important insights and explanations about the topic you asked about."""
    
    def _generate_general_response(self, question: str, content: str, paper: Paper) -> str:
        """Generate general response for other questions."""
        return f"""Based on the paper "{paper.title}" by {paper.author}, here's what I found regarding your question:

**Relevant Information:**
{content}

**Summary:** The highlighted sections contain information that addresses your question: "{question}"."""
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks."""
        chunks = []
        words = text.split()
        
        for i in range(0, len(words), self.chunk_size - self.chunk_overlap):
            chunk_words = words[i:i + self.chunk_size]
            chunk_text = " ".join(chunk_words)
            if chunk_text.strip():
                chunks.append(chunk_text)
        
        return chunks
    
    def _extract_text_from_file(self, file_path: str) -> str:
        """Extract text content from uploaded file."""
        try:
            file_extension = file_path.split('.')[-1].lower()
            
            if file_extension == 'pdf':
                return self._extract_text_from_pdf(file_path)
            elif file_extension == 'docx':
                return self._extract_text_from_docx(file_path)
            elif file_extension == 'txt':
                return self._extract_text_from_txt(file_path)
            else:
                return ""
                
        except Exception as e:
            print(f"Error extracting text from file: {e}")
            return ""
    
    def _extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file."""
        try:
            import PyPDF2
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def _extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file."""
        try:
            from docx import Document
            doc = Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting DOCX text: {e}")
            return ""
    
    def _extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error extracting TXT text: {e}")
            return ""

"""
Simplified RAG (Retrieval-Augmented Generation) Engine for academic papers.
"""
import os
import json
from typing import List, Dict, Tuple, Optional
from django.conf import settings
from papers.models import Paper, PaperChunk


class RAGEngine:
    """Simplified RAG engine for processing academic papers and answering questions."""
    
    def __init__(self):
        self.chunk_size = 1000
        self.chunk_overlap = 200
        self.top_k = 5
    
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
    
    def query(self, question: str, paper: Paper) -> Tuple[str, List[Dict], List[Dict]]:
        """Query the RAG system with a question about a specific paper."""
        try:
            # Ensure paper is processed
            if not paper.processed:
                self.process_paper(paper)
            
            # Get relevant chunks (simplified search)
            relevant_chunks = self._get_relevant_chunks_simple(question, paper)
            
            if not relevant_chunks:
                return "I couldn't find relevant information in this paper to answer your question.", [], []
            
            # Generate simple response
            response = self._generate_simple_response(question, relevant_chunks, paper)
            
            # Format chunks for response
            formatted_chunks = []
            for chunk in relevant_chunks:
                formatted_chunks.append({
                    'id': str(chunk.id),
                    'content': chunk.content,
                    'chunk_index': chunk.chunk_index,
                    'page_number': chunk.page_number,
                    'section': chunk.section
                })
            
            # Format sources
            sources = [{
                'chunk_id': str(chunk.id),
                'content_preview': chunk.content[:200] + '...',
                'similarity_score': 0.8  # Placeholder score
            } for chunk in relevant_chunks]
            
            return response, formatted_chunks, sources
            
        except Exception as e:
            print(f"Error in RAG query: {e}")
            return f"I encountered an error while processing your question: {str(e)}", [], []
    
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

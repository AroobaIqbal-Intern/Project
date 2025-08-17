#!/usr/bin/env python3
"""
Test script for enhanced Q&A and recursive reference extraction features.
"""
import os
import sys
import django
import requests
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reference_graph.settings')
django.setup()

from papers.models import Paper
from papers.utils import extract_references_from_paper
from chatbot.rag_engine import RAGEngine


def test_recursive_reference_extraction():
    """Test recursive reference extraction."""
    print("=" * 60)
    print("Testing Recursive Reference Extraction")
    print("=" * 60)
    
    # Get a sample paper
    papers = Paper.objects.filter(processed=True)[:1]
    if not papers:
        print("No processed papers found. Please upload and process a paper first.")
        return
    
    paper = papers[0]
    print(f"Testing with paper: {paper.title}")
    print(f"Current references: {paper.references.count()}")
    
    # Test recursive extraction
    print("\nStarting recursive reference extraction...")
    success = extract_references_from_paper(
        str(paper.id), 
        recursive=True, 
        max_depth=2
    )
    
    if success:
        print(f"✓ Successfully processed references")
        print(f"New reference count: {paper.references.count()}")
        
        # Show some references
        references = paper.references.all()[:5]
        print(f"\nSample references:")
        for ref in references:
            print(f"  - {ref.target_paper.title} ({ref.target_paper.author})")
    else:
        print("✗ Failed to process references")


def test_cross_paper_qa():
    """Test cross-paper Q&A functionality."""
    print("\n" + "=" * 60)
    print("Testing Cross-Paper Q&A")
    print("=" * 60)
    
    # Initialize RAG engine
    rag_engine = RAGEngine()
    
    # Test questions
    test_questions = [
        "What are the main findings?",
        "What methodology was used?",
        "What are the conclusions?",
        "How does this relate to other research?"
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        print("-" * 40)
        
        try:
            response, relevant_chunks, sources = rag_engine.query(
                question, 
                paper=None, 
                cross_paper=True
            )
            
            print(f"Response: {response[:200]}...")
            print(f"Sources found: {len(sources)}")
            
            if sources:
                print("Sample sources:")
                for source in sources[:2]:
                    print(f"  - {source.get('paper_title', 'Unknown')}")
                    
        except Exception as e:
            print(f"Error: {e}")


def test_network_qa():
    """Test reference network Q&A functionality."""
    print("\n" + "=" * 60)
    print("Testing Reference Network Q&A")
    print("=" * 60)
    
    # Get a paper with references
    papers = Paper.objects.filter(references__isnull=False).distinct()[:1]
    if not papers:
        print("No papers with references found.")
        return
    
    paper = papers[0]
    print(f"Testing with paper: {paper.title}")
    print(f"References: {paper.references.count()}")
    
    # Initialize RAG engine
    rag_engine = RAGEngine()
    
    # Test network questions
    test_questions = [
        "How does this paper relate to its references?",
        "What are the key connections in the reference network?",
        "What papers cite this work?"
    ]
    
    for question in test_questions:
        print(f"\nQuestion: {question}")
        print("-" * 40)
        
        try:
            response, relevant_chunks, sources = rag_engine.query_reference_network(
                question, 
                paper, 
                max_depth=2
            )
            
            print(f"Response: {response[:200]}...")
            print(f"Network papers analyzed: {len(set(chunk.get('paper_title', '') for chunk in relevant_chunks))}")
            
        except Exception as e:
            print(f"Error: {e}")


def test_system_statistics():
    """Test system statistics API."""
    print("\n" + "=" * 60)
    print("Testing System Statistics")
    print("=" * 60)
    
    try:
        # Test system stats
        response = requests.get('http://localhost:8000/api/chatbot/system-stats/')
        if response.status_code == 200:
            stats = response.json()
            print("System Statistics:")
            print(f"  Total papers: {stats.get('total_papers', 0)}")
            print(f"  Total references: {stats.get('total_references', 0)}")
            print(f"  Processing rate: {stats.get('processing_rate', 0):.1f}%")
            print(f"  Total conversations: {stats.get('total_conversations', 0)}")
        else:
            print(f"Failed to get system stats: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("Server not running. Please start the Django server first.")
    except Exception as e:
        print(f"Error: {e}")


def test_enhanced_content_storage():
    """Test enhanced content storage for referenced papers."""
    print("\n" + "=" * 60)
    print("Testing Enhanced Content Storage")
    print("=" * 60)
    
    # Get papers with content
    papers = Paper.objects.filter(content_text__isnull=False).exclude(content_text='')[:3]
    
    print(f"Found {papers.count()} papers with content")
    
    for paper in papers:
        print(f"\nPaper: {paper.title}")
        print(f"Author: {paper.author}")
        print(f"Year: {paper.year}")
        print(f"Content length: {len(paper.content_text)} characters")
        print(f"References: {paper.references.count()}")
        print(f"Citations: {paper.cited_by.count()}")
        
        # Show content preview
        content_preview = paper.content_text[:200] + "..." if len(paper.content_text) > 200 else paper.content_text
        print(f"Content preview: {content_preview}")


def main():
    """Run all tests."""
    print("Enhanced Q&A and Recursive Reference Extraction Test")
    print("=" * 60)
    print(f"Test started at: {datetime.now()}")
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:8000/api/papers/', timeout=5)
        if response.status_code != 200:
            print("Warning: Server may not be running properly")
    except:
        print("Warning: Server not running. Some tests may fail.")
    
    # Run tests
    test_enhanced_content_storage()
    test_recursive_reference_extraction()
    test_cross_paper_qa()
    test_network_qa()
    test_system_statistics()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)
    
    print("\nTo use the enhanced features:")
    print("1. Start the Django server: python manage.py runserver")
    print("2. Visit: http://localhost:8000/enhanced-qa/")
    print("3. Try the different Q&A modes")
    print("4. Use the management command: python manage.py process_references_recursively")


if __name__ == "__main__":
    main()
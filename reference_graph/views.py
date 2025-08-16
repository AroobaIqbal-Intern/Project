"""
Main views for the reference_graph project.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from papers.models import Paper
from papers.utils import extract_references_from_paper
import json


def home(request):
    """Home page view."""
    papers = Paper.objects.all()[:10]  # Show recent papers
    context = {
        'papers': papers,
        'total_papers': Paper.objects.count(),
    }
    return render(request, 'home.html', context)


def reference_graph(request):
    """Reference graph visualization view."""
    papers = Paper.objects.all()
    context = {
        'papers': papers,
    }
    return render(request, 'reference_graph.html', context)


def paper_detail(request, paper_id):
    """Paper detail view with zoom functionality and chatbot."""
    paper = get_object_or_404(Paper, id=paper_id)
    references = paper.references.all()
    cited_by = paper.cited_by.all()
    
    context = {
        'paper': paper,
        'references': references,
        'cited_by': cited_by,
    }
    return render(request, 'paper_detail.html', context)


@csrf_exempt
def upload_paper(request):
    """Handle paper upload and processing."""
    if request.method == 'POST':
        try:
            # Handle file upload
            uploaded_file = request.FILES.get('paper_file')
            title = request.POST.get('title', '')
            author = request.POST.get('author', '')
            
            if uploaded_file and title and author:
                # Create paper instance
                paper = Paper.objects.create(
                    title=title,
                    author=author,
                    file=uploaded_file
                )
                
                # Extract references synchronously
                extract_references_from_paper(str(paper.id))
                
                messages.success(request, 'Paper uploaded successfully! Processing references...')
                return redirect('paper_detail', paper_id=paper.id)
            else:
                messages.error(request, 'Please provide all required fields.')
                
        except Exception as e:
            messages.error(request, f'Error uploading paper: {str(e)}')
    
    return render(request, 'upload_paper.html')


def get_graph_data(request):
    """API endpoint to get graph data for visualization."""
    try:
        papers = Paper.objects.all()
        nodes = []
        edges = []
        
        for paper in papers:
            try:
                # Create a safe label by truncating and cleaning the title
                safe_title = paper.title[:50] + '...' if len(paper.title) > 50 else paper.title
                safe_title = safe_title.replace('\n', ' ').replace('\r', ' ').replace('\u25fe', '•').strip()
                
                nodes.append({
                    'id': str(paper.id),
                    'label': safe_title,
                    'title': paper.title,
                    'author': paper.author or 'Unknown Author',
                    'group': 'paper',
                    'size': 20 + (paper.citation_count * 2)  # Size based on citations
                })
                
                # Add reference edges
                for ref in paper.references.all():
                    edges.append({
                        'from': str(paper.id),
                        'to': str(ref.target_paper.id),
                        'arrows': 'to',
                        'label': 'references'
                    })
            except Exception as e:
                print(f"Error processing paper {paper.id}: {e}")
                continue
        
        return JsonResponse({
            'nodes': nodes,
            'edges': edges
        })
    except Exception as e:
        print(f"Error in get_graph_data: {e}")
        return JsonResponse({
            'error': str(e),
            'nodes': [],
            'edges': []
        }, status=500)


def test_graph(request):
    """Test page for graph visualization."""
    return render(request, 'test_graph.html')

def chatbot_test(request):
    """Test page for chatbot functionality."""
    return render(request, 'chatbot_test.html')

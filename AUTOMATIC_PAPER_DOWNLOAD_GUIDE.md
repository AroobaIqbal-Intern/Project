# Automatic Paper Download System

## 🚀 **Overview**

This system automatically downloads academic papers from the internet and creates a complete reference network. When you upload a paper, the system will:

1. **Extract references** from the uploaded paper
2. **Download referenced papers** from various online sources
3. **Recursively extract references** from downloaded papers
4. **Create a complete network** where all papers show full content
5. **Enable chatbot to answer questions** from all papers in the network

## 🔧 **How It Works**

### **1. Paper Upload Process**

When you upload a paper:

```python
# 1. Paper is uploaded and saved
paper = Paper.objects.create(title=title, author=author, file=uploaded_file)

# 2. Background processing starts
def process_paper_background():
    downloaded_papers = recursive_extractor.process_uploaded_paper(paper)
    print(f"Downloaded {len(downloaded_papers)} papers")

# 3. Background thread runs
thread = threading.Thread(target=process_paper_background)
thread.start()
```

### **2. Recursive Reference Extraction**

The system follows this process:

1. **Process uploaded paper** with RAG engine
2. **Extract references** from paper content
3. **For each reference**:
   - Try to download from online sources
   - If successful, process the downloaded paper
   - Recursively extract references from downloaded paper
4. **Repeat** up to 3 levels deep

### **3. Download Sources**

The system tries multiple sources in order:

1. **arXiv** - For preprints and published papers
2. **DOI** - Direct links to publisher websites
3. **Semantic Scholar** - Academic search engine
4. **ResearchGate** - Academic social network
5. **Google Scholar** - General academic search

## 📁 **Files Added/Modified**

### **New Files:**
- `papers/paper_downloader.py` - Core download functionality
- `test_recursive_download.py` - Test script
- `AUTOMATIC_PAPER_DOWNLOAD_GUIDE.md` - This documentation

### **Modified Files:**
- `papers/views.py` - Enhanced upload view
- `papers/urls.py` - Added download endpoint
- `reference_graph/views.py` - Enhanced frontend upload
- `templates/paper_detail.html` - Progress tracking UI
- `chatbot/views.py` - Enhanced chat functionality

## 🎯 **Key Features**

### **1. Automatic Download**
- Downloads papers from multiple sources
- Handles different file formats (PDF, DOCX, TXT)
- Stores files in organized directory structure

### **2. Recursive Processing**
- Extracts references from downloaded papers
- Creates a complete reference network
- Limits recursion depth to prevent infinite loops

### **3. Progress Tracking**
- Real-time progress updates
- Download status indicators
- User-friendly progress bars

### **4. Enhanced Chatbot**
- Works with all papers in the network
- Suggests downloading missing papers
- Provides comprehensive answers

### **5. Smart Matching**
- Prevents duplicate downloads
- Matches papers by title, author, and year
- Handles variations in paper metadata

## 🔄 **Usage Workflow**

### **1. Upload a Paper**
```bash
# Go to upload page
http://localhost:8000/upload/

# Fill in paper details and upload file
# System automatically starts background processing
```

### **2. Monitor Progress**
```bash
# Check paper detail page
http://localhost:8000/papers/<paper-id>/

# Click "Check Download Progress" to see status
# Progress bar shows current download status
```

### **3. View Reference Network**
```bash
# All referenced papers will be available
# Click on any reference to view full content
# Chatbot can answer questions about any paper
```

### **4. Manual Download**
```bash
# For papers that couldn't be downloaded automatically
# Click "Download" button next to reference
# System will try to find and download the paper
```

## 🛠 **Configuration**

### **Download Settings**
```python
# In papers/paper_downloader.py
class RecursiveReferenceExtractor:
    def __init__(self, downloader: PaperDownloader):
        self.max_depth = 3  # Maximum recursion depth
        self.processed_papers = set()  # Prevent duplicates
```

### **Download Sources**
```python
# Available download methods
download_methods = [
    self._download_from_arxiv,
    self._download_from_doi,
    self._download_from_semantic_scholar,
    self._download_from_researchgate,
    self._download_from_google_scholar
]
```

### **File Storage**
```python
# Downloaded files are stored in
self.download_path = os.path.join(settings.MEDIA_ROOT, 'papers', 'downloaded')
```

## 📊 **API Endpoints**

### **Download Paper**
```bash
POST /api/papers/<paper-id>/download/
Content-Type: application/json

Response:
{
    "success": true,
    "message": "Paper downloaded and processed successfully"
}
```

### **Process References**
```bash
POST /api/papers/<paper-id>/process-references/
Content-Type: application/json

Response:
{
    "message": "Reference extraction completed successfully",
    "references_found": 15
}
```

### **Enhanced Chat**
```bash
POST /api/chatbot/papers/<paper-id>/chat/
Content-Type: application/json

{
    "message": "What are the main findings?",
    "session_id": "session_123"
}

Response:
{
    "assistant_message": {
        "content": "The main findings are...",
        "relevant_chunks": [...]
    },
    "sources": [...],
    "referenced_papers": [...]
}
```

## 🧪 **Testing**

### **Run Test Script**
```bash
# Activate virtual environment
source venv/bin/activate

# Run test script
python test_recursive_download.py
```

### **Test Individual Components**
```python
# Test paper downloader
from papers.paper_downloader import paper_downloader
success = paper_downloader.download_paper(paper)

# Test recursive extraction
from papers.paper_downloader import recursive_extractor
downloaded_papers = recursive_extractor.process_uploaded_paper(paper)
```

## 🔍 **Troubleshooting**

### **Common Issues**

1. **Download Fails**
   - Check internet connection
   - Verify paper title/author accuracy
   - Try manual download button

2. **Processing Stuck**
   - Check background thread status
   - Restart Django server
   - Check logs for errors

3. **Memory Issues**
   - Reduce max_depth in RecursiveReferenceExtractor
   - Limit number of concurrent downloads
   - Monitor system resources

### **Debug Mode**
```python
# Enable detailed logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Check download progress
from papers.paper_downloader import paper_downloader
paper_downloader.download_paper(paper, debug=True)
```

## 🚀 **Future Enhancements**

### **Planned Features**
1. **Parallel Downloads** - Download multiple papers simultaneously
2. **Citation Network Analysis** - Analyze paper relationships
3. **Paper Recommendations** - Suggest related papers
4. **Advanced Search** - Search across all downloaded papers
5. **Collaborative Features** - Share paper networks

### **Performance Optimizations**
1. **Caching** - Cache downloaded papers
2. **Compression** - Compress stored files
3. **Indexing** - Fast search across papers
4. **Background Tasks** - Use Celery for processing

## 📈 **Performance Metrics**

### **Expected Results**
- **Download Success Rate**: 60-80% (depends on paper availability)
- **Processing Time**: 2-5 minutes per paper
- **Network Depth**: 3 levels (configurable)
- **Storage**: ~5-10MB per paper

### **Monitoring**
```python
# Check system status
from papers.models import Paper
total_papers = Paper.objects.count()
papers_with_files = Paper.objects.filter(file__isnull=False).count()
success_rate = papers_with_files / total_papers * 100
print(f"Download success rate: {success_rate:.1f}%")
```

## 🎉 **Conclusion**

The automatic paper download system creates a comprehensive academic reference network that:

- **Automatically downloads** referenced papers from the internet
- **Creates a complete network** of interconnected papers
- **Enables comprehensive chatbot** that can answer questions from all papers
- **Provides user-friendly interface** with progress tracking
- **Handles edge cases** and provides fallback options

This system transforms your paper management from a manual process into an automated, intelligent network that grows with each uploaded paper!
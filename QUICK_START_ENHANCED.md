# Quick Start Guide - Enhanced Q&A & Recursive References

## 🚀 Getting Started

### 1. Start the Server
```bash
python manage.py runserver
```

### 2. Access the Enhanced Q&A Interface
Navigate to: http://localhost:8000/enhanced-qa/

### 3. Upload Some Papers
1. Go to http://localhost:8000/upload/
2. Upload a few academic papers (PDF, DOCX, or TXT)
3. Wait for processing to complete

### 4. Process References Recursively
```bash
# Process all papers with depth 3
python manage.py process_references_recursively --max-depth 3

# Or process a specific paper
python manage.py process_references_recursively --paper-id <paper_id> --max-depth 2
```

## 🎯 Try the Enhanced Features

### Cross-Paper Q&A
1. Go to the Enhanced Q&A interface
2. Select "Cross-Paper Search" mode
3. Ask questions like:
   - "What are the main findings about machine learning?"
   - "What methodologies are commonly used?"
   - "What are the key conclusions across all papers?"

### Single Paper Q&A
1. Select "Single Paper" mode
2. Choose a paper from the dropdown
3. Ask questions like:
   - "What methodology did this paper use?"
   - "What are the main findings?"
   - "What are the limitations mentioned?"

### Reference Network Q&A
1. Select "Reference Network" mode
2. Choose a paper as the starting point
3. Ask questions like:
   - "How does this paper relate to its references?"
   - "What papers cite this work?"
   - "What are the key connections in the network?"

## 🔧 Management Commands

### Process References
```bash
# Process all papers recursively
python manage.py process_references_recursively

# Process with specific depth
python manage.py process_references_recursively --max-depth 3

# Process specific paper
python manage.py process_references_recursively --paper-id <paper_id>

# Dry run (see what would be processed)
python manage.py process_references_recursively --dry-run
```

### Check System Status
```bash
# Check paper status
python manage.py paper_status

# Test reference extraction
python manage.py extract_references

# Process papers for RAG
python manage.py process_papers_for_rag
```

## 📊 API Endpoints

### Cross-Paper Q&A
```bash
POST /api/chatbot/cross-paper-chat/
{
    "message": "What are the main findings?",
    "max_papers": 10
}
```

### Network Q&A
```bash
POST /api/chatbot/network-chat/{paper_id}/
{
    "message": "How does this relate to other papers?",
    "max_depth": 2
}
```

### System Statistics
```bash
GET /api/chatbot/system-stats/
GET /api/chatbot/papers/{paper_id}/network-stats/
GET /api/chatbot/search-papers/?q=query&max_results=10
```

## 🧪 Testing

### Run the Test Script
```bash
python test_enhanced_features.py
```

### Manual Testing
1. Upload a paper with references
2. Process references recursively
3. Try different Q&A modes
4. Check the reference graph visualization

## 📈 Expected Results

### After Recursive Processing:
- Papers will have references extracted
- Referenced papers will have content (even without uploaded files)
- Reference network will be built
- Cross-paper Q&A will work across the entire collection

### Q&A Capabilities:
- **Cross-Paper**: Answers from multiple papers
- **Single Paper**: Deep analysis of individual papers
- **Network**: Reference network exploration
- **Source Attribution**: All answers show their sources

## 🔍 Troubleshooting

### Common Issues:

1. **No papers found for Q&A**
   - Upload some papers first
   - Ensure papers are processed (`processed=True`)

2. **No references extracted**
   - Check if papers have content
   - Run reference extraction manually
   - Check for errors in processing

3. **Q&A not working**
   - Ensure RAG engine is working
   - Check if papers have chunks created
   - Verify API endpoints are accessible

4. **Server errors**
   - Check Django logs
   - Ensure all dependencies are installed
   - Verify database migrations are applied

### Debug Commands:
```bash
# Check paper status
python manage.py shell
>>> from papers.models import Paper
>>> Paper.objects.filter(processed=True).count()

# Check references
>>> from papers.models import Reference
>>> Reference.objects.count()

# Test RAG engine
>>> from chatbot.rag_engine import RAGEngine
>>> rag = RAGEngine()
>>> rag.query("test question", paper=None, cross_paper=True)
```

## 🎉 Success Indicators

You'll know everything is working when:

1. ✅ Papers upload and process successfully
2. ✅ References are extracted recursively
3. ✅ Enhanced Q&A interface loads
4. ✅ Cross-paper questions return answers
5. ✅ Network Q&A shows relationships
6. ✅ Sources are displayed for all answers
7. ✅ System statistics show data

## 📚 Next Steps

1. **Explore the Reference Graph**: Visit `/graph/` to see the visual network
2. **Upload More Papers**: Build a larger knowledge base
3. **Try Complex Questions**: Ask about relationships and trends
4. **Customize Settings**: Adjust processing parameters
5. **Extend Functionality**: Add new Q&A modes or features

## 🆘 Need Help?

- Check the full documentation: `ENHANCED_QA_FEATURES.md`
- Review the original improvements: `REFERENCE_EXTRACTION_IMPROVEMENTS.md`
- Run the test script: `python test_enhanced_features.py`
- Check Django logs for errors
- Verify all requirements are installed

---

**Happy exploring your academic knowledge graph! 🚀**
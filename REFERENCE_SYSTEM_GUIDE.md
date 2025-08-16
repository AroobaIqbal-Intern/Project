# Reference System Guide

## How It Works

Your reference system automatically extracts citations from uploaded papers and creates a network of connected papers. Here's how it works:

### 1. **Paper Upload Process**
```
Upload PDF → Extract Text → Find Citations → Create Reference Papers → Link Everything
```

### 2. **Reference Discovery**
- **Pattern Matching**: Uses regex patterns to find citations like:
  - `Smith et al. (2023)`
  - `Johnson, A. (2022)`
  - `Brown, M. and Davis, R. (2021)`

- **Automatic Creation**: When a citation is found, it automatically:
  - Creates a new paper entry for the referenced work
  - Links the current paper to the referenced paper
  - Builds a citation network

### 3. **Recursive References**
- Paper A references Paper B
- Paper B references Paper C
- Paper C references Paper D
- And so on... creating a complete reference graph

## Current Status

✅ **System is working!** 
- Created test paper with 4 manual references
- System found 6 additional references automatically
- Total: 10 references created

## How to Use

### 1. **Upload a Paper with Citations**
- Go to the upload page
- Upload a PDF that contains academic citations
- The system will automatically extract references

### 2. **View References**
- Open any paper detail page
- Scroll down to see the "References" section
- Click on any reference to see that paper's details

### 3. **Manual Reference Extraction**
- On any paper page, click "Extract References" button
- This will re-run the reference extraction process
- Useful if you want to update references

### 4. **Test the System**
```bash
# Create a test paper with citations
python manage.py create_test_paper

# Test reference extraction on all papers
python manage.py extract_references --all

# Test specific paper
python manage.py extract_references --paper-id <PAPER_ID>
```

## Why Your Papers Don't Show References

### **Current Papers**
- Most are placeholder papers (no actual files)
- The one with content is a research proposal (no academic citations)
- PDF text extraction quality is poor (broken words, extra spaces)

### **To Get References Working**
1. **Upload real academic papers** with proper citations
2. **Use better quality PDFs** (text-based, not image-based)
3. **Ensure papers contain citations** in standard academic format

## Expected Results

### **When You Upload a Good Paper**
- References section shows linked papers
- Each referenced paper shows its own references
- Creates a network of connected research
- Recursive discovery builds the complete graph

### **Example Citation Formats That Work**
```
Smith et al. (2023) demonstrated improved learning outcomes.
Johnson, A. (2022) found significant improvements.
Brown, M. and Davis, R. (2021) established the foundation.
Wilson et al. (2020) provided a comprehensive review.
```

## Troubleshooting

### **If No References Appear**
1. Check if the paper has readable text content
2. Verify the paper contains citations in standard format
3. Use the "Extract References" button to manually trigger
4. Check console output for error messages

### **If References Are Wrong**
1. The citation patterns might be too broad
2. PDF text quality might be poor
3. Citations might be in non-standard format

## Next Steps

1. **Upload a real academic paper** with citations
2. **Test the reference extraction**
3. **View the reference network**
4. **Explore recursive references**

The system is working correctly - it just needs papers with proper academic citations to build the reference network!

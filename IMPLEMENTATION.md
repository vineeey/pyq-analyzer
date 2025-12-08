# PYQ Analyzer - Implementation Guide

## Overview
This document describes the implementation of the Django web application for analyzing Previous Year Question Papers (PYQs).

## Features Implemented

### 1. Core Data Models

#### TopicCluster Model
- Tracks repeated questions grouped as topics
- Fields: topic_name, normalized_key, frequency_count, years_appeared, priority_tier
- Supports priority tiers 1-4 based on repetition frequency
- Stores embedding centroids for cluster similarity

#### SubjectAnalytics Model
- Caches computed analytics for fast dashboard loading
- Fields: total_questions, unique_topics, tier distributions
- Tracks top topics by module
- Auto-updates on clustering

#### Enhanced Subject Model
- Added `exam_pattern` JSONField for configurable mappings
- Added `tier_thresholds` JSONField for priority configuration
- Methods: get_exam_pattern(), set_exam_pattern(), get_tier_thresholds()

#### Enhanced Question Model
- Added `topic_cluster` ForeignKey for clustering
- Added `normalized_text` TextField for matching
- Links questions to their topic clusters

### 2. Exam Pattern System

#### Predefined Patterns (`apps/subjects/exam_patterns.py`)
- **KTU Standard Pattern**: Part A (Q1-Q10), Part B (Q11-Q20), 5 modules
- **Generic 5-Module Pattern**: Flexible 5-module mapping
- **Generic 6-Module Pattern**: Flexible 6-module mapping

#### Pattern Configuration
- Stored as JSON in Subject model
- Maps question numbers to modules by part
- Includes marks per question
- Example:
```python
{
  "part_a": {
    "marks_per_question": 3,
    "questions": {"1": 1, "2": 1, "3": 2, ...}
  },
  "part_b": {
    "marks_per_question": 14,
    "questions": {"11": 1, "12": 1, ...}
  }
}
```

### 3. PDF Extraction & Question Parsing

#### QuestionExtractor Service
- Extracts text using pdfplumber (primary) and PyMuPDF (fallback)
- Parses Part A and Part B questions separately
- Handles KTU-style format with OCR artifacts
- Applies exam pattern mapping to assign module hints
- Deduplicates extracted questions

#### Extraction Features
- Cleans OCR artifacts and formatting issues
- Identifies question numbers, marks, and text
- Supports sub-questions (11a, 11b, etc.)
- Fallback extraction for difficult PDFs

### 4. Topic Clustering System

#### TextNormalizer Service
- Normalizes question text for comparison
- Removes years, marks, stopwords
- Extracts key phrases for topic naming
- Creates concise topic keys for lookups

#### TopicClusterer Service
- Groups similar questions using cosine similarity
- Uses embeddings (if available) or Jaccard similarity (fallback)
- Configurable similarity threshold (default 0.75)
- Generates human-readable topic names
- Tracks frequency, years, marks per topic

#### Clustering Process
1. Normalize all question texts
2. Build similarity matrix using embeddings
3. Group questions above threshold into clusters
4. Assign topic name from representative question
5. Calculate statistics (frequency, years, marks)
6. Assign priority tiers based on thresholds
7. Link questions to their clusters

### 5. Module-wise PDF Generation

#### ModuleReportGenerator
- Generates individual PDFs per module
- Uses WeasyPrint for high-quality output
- Professional styling with CSS

#### Report Structure
1. **Header**: Module name, subject, university
2. **Part A Questions**: Grouped by year with marks
3. **Part B Questions**: Grouped by year with marks
4. **Repeated Question Analysis**:
   - Tier 1 (Top Priority): 4+ repetitions
   - Tier 2 (High Priority): 3 repetitions
   - Tier 3 (Medium Priority): 2 repetitions
   - Tier 4 (Low Priority): 1 repetition
5. **Study Priority Order**: Ranked list of topics

#### Styling Features
- Color-coded priority tiers (red, orange, green, blue)
- Frequency badges showing repetition count
- Years appeared listed for each topic
- Professional typography and spacing
- Responsive to different content lengths

### 6. Analytics Dashboard

#### StatsCalculator Service
- Computes comprehensive statistics
- Methods:
  - `get_overview()`: Total papers, questions, topics
  - `get_module_distribution()`: Question counts per module
  - `get_topic_clusters_by_module()`: Clustered topics
  - `get_priority_distribution()`: Topics per tier
  - `get_top_topics_by_module()`: Top N topics per module
  - `cache_analytics()`: Store results in SubjectAnalytics

#### Dashboard Charts (Chart.js)
- Module distribution bar chart
- Bloom's taxonomy doughnut chart
- Difficulty distribution pie chart
- Year-wise trend line chart
- Topic priority horizontal bar chart (via API)

#### API Endpoints
- `/analytics/subject/<id>/api/`: Complete stats JSON
- `/analytics/subject/<id>/api/topic-priority/`: Chart data for top topics

### 7. Web UI & Workflows

#### Subject Actions
- **Analyze Papers** (`/subjects/<id>/analyze/`):
  - Processes all pending papers
  - Extracts questions with pattern mapping
  - Triggers clustering in background
  - Shows success/error messages

- **Trigger Clustering** (`/subjects/<id>/cluster/`):
  - Manually runs clustering on existing questions
  - Updates topic clusters and priorities
  - Caches analytics for dashboard

- **Configure Pattern** (`/subjects/<id>/configure-pattern/`):
  - Sets exam pattern for subject
  - Affects future paper analysis

#### Report Management
- **Module Reports View** (`/reports/subject/<id>/modules/`):
  - Lists all modules with report status
  - Generate all button
  - Individual download links
  - View/download existing PDFs

- **Generate All** (`/reports/subject/<id>/modules/generate-all/`):
  - Creates PDFs for all modules
  - Shows progress and results

- **Download Module** (`/reports/subject/<id>/modules/<module_id>/download/`):
  - Serves individual module PDF

### 8. Background Tasks (Django-Q2)

#### Async Task: cluster_subject_topics
- Runs clustering for a subject
- Called after paper analysis
- Updates analytics cache
- Returns stats on completion

#### Async Task: update_subject_analytics
- Refreshes cached analytics
- Called on data changes
- Ensures dashboard stays current

### 9. Performance Optimizations

#### Caching Strategy
- Analytics cached in SubjectAnalytics model
- Regenerated only on clustering or new papers
- Dashboard loads from cache for speed

#### Batch Operations
- Extract all questions from paper at once
- Generate all embeddings in batch
- Cluster all questions per module together
- Generate all module PDFs in single call

#### Query Optimization
- Use `select_related()` for foreign keys
- Use `prefetch_related()` for reverse relations
- Index on normalized_key for fast lookups
- Filter deleted objects with SoftDeleteManager

#### Resource Management
- CPU-only operation (no GPU needed)
- Lightweight MiniLM embedding model
- Background tasks prevent UI blocking
- Configurable worker count

### 10. Security Considerations

#### Input Validation
- File type validation for PDFs
- File size limits (10MB default)
- User ownership checks on all views
- CSRF protection on forms

#### Data Protection
- LoginRequiredMixin on all views
- OwnerRequiredMixin for user data
- Soft delete for data recovery
- No sensitive data in logs

#### SQL Injection Prevention
- Django ORM parameterized queries
- No raw SQL with user input
- Validated foreign key references

## File Structure

```
pyq-analyzer/
├── apps/
│   ├── subjects/
│   │   ├── models.py          # Subject, Module models
│   │   ├── exam_patterns.py   # Pattern definitions
│   │   ├── views.py           # CRUD views
│   │   ├── actions.py         # Analyze, cluster actions
│   │   └── urls.py
│   ├── papers/
│   │   ├── models.py          # Paper, PaperPage models
│   │   └── ...
│   ├── questions/
│   │   ├── models.py          # Question model
│   │   └── ...
│   ├── analytics/
│   │   ├── models.py          # TopicCluster, SubjectAnalytics
│   │   ├── calculator.py      # StatsCalculator
│   │   ├── tasks.py           # Async tasks
│   │   ├── views.py           # Dashboard, APIs
│   │   └── urls.py
│   ├── reports/
│   │   ├── generator.py       # ReportGenerator
│   │   ├── module_generator.py # ModuleReportGenerator
│   │   ├── views.py           # Report views
│   │   └── urls.py
│   └── analysis/
│       ├── pipeline.py        # AnalysisPipeline
│       └── services/
│           ├── extractor.py   # QuestionExtractor
│           ├── classifier.py  # ModuleClassifier
│           ├── embedder.py    # EmbeddingService
│           └── similarity.py  # SimilarityService
├── services/
│   └── clustering/
│       ├── topic_clusterer.py # TopicClusterer
│       └── normalizer.py      # TextNormalizer
├── templates/
│   ├── analytics/
│   │   └── dashboard.html     # Dashboard with charts
│   └── reports/
│       ├── module_reports.html      # Report list UI
│       └── module_wise_report.html  # PDF template
├── config/
│   ├── settings.py
│   └── urls.py
└── manage.py
```

## Usage Flow

1. **Setup**:
   - Create subject with exam pattern
   - Add modules with keywords

2. **Upload**:
   - Upload question paper PDFs
   - Papers enter PENDING status

3. **Analysis**:
   - Click "Analyze All Papers"
   - QuestionExtractor parses PDFs
   - Questions classified to modules
   - Embeddings generated
   - Clustering triggered async

4. **Clustering**:
   - TopicClusterer groups similar questions
   - Frequency and years tracked
   - Priority tiers assigned
   - Analytics cached

5. **Reports**:
   - Generate module-wise PDFs
   - Download individual modules
   - Share with students

6. **Dashboard**:
   - View charts and statistics
   - See top repeated topics
   - Track coverage and priorities

## Configuration

### Environment Variables (.env)
```bash
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db/pyq_analyzer.sqlite3
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Django Settings
```python
# Priority Thresholds (default)
{
    'tier_1': 4,  # 4+ exams
    'tier_2': 3,  # 3 exams
    'tier_3': 2,  # 2 exams
}

# Clustering Threshold (default)
similarity_threshold = 0.75  # 0.0-1.0

# File Upload Limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
```

## Testing

### Unit Tests
- Test question extraction with sample PDFs
- Test clustering with known similar questions
- Test priority assignment logic
- Test PDF generation

### Integration Tests
- Full workflow: upload → analyze → cluster → report
- Multi-paper analysis
- Dashboard data accuracy

### Performance Tests
- Large paper extraction time
- Clustering with 1000+ questions
- Report generation speed
- Dashboard load time with cache

## Future Enhancements

### Potential Features
- OCR for scanned PDFs (pytesseract integration)
- Multiple exam pattern support per subject
- Question tagging and manual clustering
- Export to Excel/CSV
- Mobile-responsive design
- User collaboration features
- Syllabus-based topic mapping

### Scalability
- PostgreSQL for production
- Celery for distributed tasks
- Redis for caching
- S3 for file storage
- Elasticsearch for search

## Maintenance

### Regular Tasks
- Clear old analytics cache (monthly)
- Archive old papers (yearly)
- Update embedding model (as needed)
- Review clustering thresholds

### Monitoring
- Check Django-Q task queue
- Monitor disk space (PDFs, reports)
- Review error logs
- Track clustering accuracy

## Conclusion

This implementation provides a complete, production-ready system for PYQ analysis with:
- Automated question extraction
- Intelligent topic clustering
- Priority-based study guidance
- Professional PDF reports
- Visual analytics dashboard
- Background task processing
- Security and performance optimizations

The system runs efficiently on low-spec hardware and requires no external paid services.

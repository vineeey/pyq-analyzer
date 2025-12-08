# PYQ Analyzer — Zero-Cost Edition

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11+-brightgreen.svg)
![Django](https://img.shields.io/badge/django-5.0+-green.svg)

**PYQ Analyzer** is an AI-powered web application for analyzing Previous Year Question (PYQ) papers. It automatically extracts questions, groups them into modules, identifies repeated topics, assigns priority levels, and generates comprehensive study reports.

## ✨ Features

- 📄 **PDF Upload & Processing**: Upload multiple PYQ PDFs and extract questions automatically
- 🔍 **Intelligent Question Extraction**: Parse text-based and scanned PDFs with OCR support
- 🎯 **Module Mapping**: Configurable exam patterns to map questions to modules
- 🤖 **AI-Powered Analysis**: 
  - Topic clustering using sentence embeddings
  - Similarity detection for repeated questions
  - Bloom's taxonomy classification
  - Difficulty estimation
- 📊 **Analytics Dashboard**: Visual insights on topic frequency, repetition patterns, and priority levels
- 📑 **Report Generation**: Clean, module-wise PDF reports with prioritized study plans
- 🎨 **Modern UI**: Beautiful, responsive interface built with Tailwind CSS
- 💰 **Zero Cost**: Runs entirely on local/free resources (SQLite, Ollama, local embeddings)

## 🏗️ Architecture

### Technology Stack

- **Backend**: Django 5.x, Python 3.11+
- **Database**: SQLite3 with WAL mode
- **AI/ML**: 
  - Ollama + Llama 3.2 3B (local LLM)
  - sentence-transformers (all-MiniLM-L6-v2)
  - spaCy for NLP
- **PDF Processing**: pdfplumber, PyMuPDF, pytesseract
- **Frontend**: Tailwind CSS, Alpine.js, HTMX
- **Report Generation**: WeasyPrint (HTML to PDF)
- **Task Queue**: Django-Q2 (SQLite-based)

## 📋 Prerequisites

- Python 3.11 or higher
- 8GB RAM minimum (16GB recommended)
- 10GB free disk space
- Node.js (for Tailwind CSS compilation)
- Ollama (for local LLM)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/vineeey/pyq-analyzer.git
cd pyq-analyzer
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Download AI Models

```bash
# Download sentence-transformers and spaCy models
python scripts/download_models.py
```

### 4. Set Up Ollama

```bash
# Run the setup script (Linux/Mac)
bash scripts/setup_ollama.sh

# Or manually:
# 1. Install Ollama from https://ollama.com/download
# 2. Pull the required model:
ollama pull llama3.2:3b
```

### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings (optional for development)
```

### 6. Initialize Database

```bash
# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# (Optional) Load sample data
python manage.py loaddata sample_data
```

### 7. Build Frontend Assets

```bash
# Install Node dependencies
npm install

# Build Tailwind CSS
npx tailwindcss -i ./static/css/input.css -o ./static/css/output.css --watch
```

### 8. Run Development Server

```bash
# In a new terminal (keep Tailwind running in the other)
python manage.py runserver
```

Visit `http://127.0.0.1:8000` in your browser.

## 📖 Usage

### Creating a Subject

1. Log in to your account
2. Navigate to **Subjects** → **Create New Subject**
3. Enter subject details (name, code, scheme, university)
4. Define modules and their configurations
5. Set up the exam pattern (question-to-module mapping)

### Uploading PYQ Papers

1. Select a subject
2. Click **Upload Paper**
3. Choose PDF file(s) and enter exam details (year, semester)
4. The system will automatically extract and classify questions

### Defining Classification Rules

1. Navigate to **Rules** → **Create Rule**
2. Write rules in plain English (e.g., "Questions about layers of atmosphere belong to Module 1")
3. The local LLM will compile your rules into executable code
4. Apply rules to classify questions automatically

### Generating Reports

1. Go to a subject's detail page
2. Click **Generate Report**
3. Select modules and report options
4. Download the PDF with:
   - All questions organized by module and year
   - Repeated topic analysis
   - Prioritized study plan

## 🔧 Configuration

### Database Settings

Edit `config/settings.py` to customize SQLite configuration:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db' / 'pyq_analyzer.sqlite3',
        'OPTIONS': {
            'timeout': 30,
        },
    }
}
```

### Ollama Configuration

Configure the Ollama endpoint in your `.env` file:

```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

### Priority Thresholds

Adjust topic priority thresholds in subject settings:
- Tier 1 (Top Priority): Appears in 4+ exams
- Tier 2 (High Priority): Appears in 3 exams
- Tier 3 (Medium Priority): Appears in 2 exams
- Tier 4 (Low Priority): Appears in 1 exam

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps --cov-report=html

# Run specific test module
pytest apps/questions/tests/
```

## 📦 Project Structure

```
pyq-analyzer/
├── apps/                      # Django applications
│   ├── analysis/             # AI analysis engine
│   ├── analytics/            # Statistics & dashboards
│   ├── core/                 # Shared utilities
│   ├── papers/               # PDF upload & management
│   ├── questions/            # Extracted questions
│   ├── reports/              # PDF report generation
│   ├── rules/                # Classification rules
│   ├── subjects/             # Subject management
│   └── users/                # Authentication
├── config/                   # Django settings
├── scripts/                  # Setup & utility scripts
├── services/                 # Core services
│   ├── embedding/           # Sentence embeddings
│   └── llm/                 # Ollama client
├── static/                   # Static files (CSS, JS)
├── templates/                # HTML templates
├── manage.py
└── requirements.txt
```

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Ollama](https://ollama.com/) for local LLM infrastructure
- [Sentence Transformers](https://www.sbert.net/) for embedding models
- [Django](https://www.djangoproject.com/) for the web framework
- The open-source community for amazing tools and libraries

## 📧 Support

For issues, questions, or suggestions:
- Open an [issue](https://github.com/vineeey/pyq-analyzer/issues)
- Contact: [GitHub Profile](https://github.com/vineeey)

## 🗺️ Roadmap

- [ ] Support for more exam patterns (CBSE, ICSE, etc.)
- [ ] Multi-language support for question papers
- [ ] Collaborative features (sharing subjects/reports)
- [ ] Mobile app (React Native)
- [ ] Integration with learning management systems
- [ ] Advanced analytics (study time estimation, difficulty progression)

---

**Made with ❤️ for students everywhere**

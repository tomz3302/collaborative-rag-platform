# Collaborative RAG Learning Platform

> A state-of-the-art Retrieval-Augmented Generation (RAG) system designed for college students to collaboratively learn, share insights, and build knowledge together.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-latest-orange.svg)](https://www.langchain.com/)
[![Google Gemini](https://img.shields.io/badge/Gemini-2.5--flash-red.svg)](https://ai.google.dev/)

---

## Overview

This project is an experimental platform that combines cutting-edge RAG technology with social collaboration features to enhance the learning experience for college students. Instead of studying in isolation, students can create shared spaces for each course, collaborate on understanding complex materials, and learn from each other's questions and insights.

### Vision

Build a collaborative learning environment where:
- **Each course has its own dedicated workspace** (notebook/space)
- **Students can join course spaces** and contribute to collective knowledge
- **Every PDF page becomes a discussion thread** where students see what others asked about that specific content
- **Moderator-driven quality control** ensures accurate and helpful contributions (pull-request style workflow)
- **Intelligent, context-aware RAG** adapts to different document types (lectures, notes, textbooks, transcripts)
- **Shared artifacts** allow students to benefit from each other's queries and discoveries

---

## Current Features

### Advanced RAG Pipeline
- **Hybrid Retrieval**: Combines FAISS vector search with BM25 keyword search for optimal document retrieval
- **Cross-Encoder Reranking**: Uses `BAAI/bge-reranker-base` for precision ranking
- **Contextual Embeddings**: Leverages Google's Gemini 2.5 Flash to generate context-aware chunk embeddings
- **Source Attribution**: Returns the source document with each answer for transparency
- **High Performance**: Optimized for speed with Gemini 2.5 Flash LLM

### Web Interface
- **FastAPI Backend**: RESTful API for document upload and query processing
- **PDF Upload**: Simple document ingestion pipeline
- **Chat Interface**: Interactive question-answering system
- **Modern UI**: Clean, responsive web interface

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       FastAPI Server                         │
│                     (rag_server.py)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Advanced RAG System                         │
│                  (advanced_rag.py)                           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   Document   │  │   Hybrid     │  │  Cross-      │        │
│  │  Processing  │─▶│  Retrieval   │─▶│  Encoder     │       │
│  │              │  │ (FAISS+BM25) │  │  Reranking   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│         │                                      │             │
│         ▼                                      ▼             │
│  ┌──────────────┐                    ┌──────────────┐        │
│  │ Contextual   │                    │   Gemini     │        │
│  │ Embeddings   │                    │   LLM        │        │
│  └──────────────┘                    └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **LLM**: Google Gemini 2.5 Flash
- **Embeddings**: Google `text-embedding-004`
- **Vector Store**: FAISS
- **Keyword Search**: BM25
- **Reranker**: HuggingFace Cross-Encoder (`BAAI/bge-reranker-base`)
- **Framework**: LangChain
- **API**: FastAPI
- **PDF Processing**: PyPDFLoader

---

## Getting Started

### Prerequisites
- Python 3.11 or higher
- Google API Key (for Gemini access)
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd PythonProject2
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Required packages:
   - `fastapi`
   - `uvicorn`
   - `langchain`
   - `langchain-community`
   - `langchain-google-genai`
   - `langchain-core`
   - `faiss-cpu` (or `faiss-gpu`)
   - `sentence-transformers`
   - `pypdf`
   - `numpy`
   - `python-multipart`
   - `mysql-connector-python`
   - `sentence-transformers`
   - `rank_bm25`
   - `aiomysql`
   - `cryptography`
   - `fastapi-users-db-sqlalchemy`
   - `fastapi-users`
   - `fastapi-mail`
   - `supabase`
   - `requests`
3. **Set up environment variables**
   ```bash
   # Windows PowerShell
   $env:GOOGLE_API_KEY="your-google-api-key-here"
   $env:GROQ_API_KEY="your-groq-api-key-here"
   $env:SUPABASE_URL="your-supabase-project-url"
   $env:SUPABASE_KEY="your-supabase-anon-key"
   
   # Linux/Mac
   export GOOGLE_API_KEY="your-google-api-key-here"
   export GROQ_API_KEY="your-groq-api-key-here"
   export SUPABASE_URL="your-supabase-project-url"
   export SUPABASE_KEY="your-supabase-anon-key"
   ```

4. **Set up Supabase Storage** (See [Supabase Configuration](#supabase-configuration) section below)

4. **Run the server**
   ```bash
   cd backend
   python rag_server.py
   ```
   
   The server will start at `http://localhost:8000`

---

## Supabase Configuration

This project uses **Supabase Storage** for cloud-based PDF document storage and retrieval, enabling scalable file management without local storage limitations.

### Why Supabase?

- **Cloud Storage**: PDFs are stored in Supabase buckets, accessible via public URLs
- **Scalability**: No local disk space limitations
- **Accessibility**: Documents can be accessed from anywhere via HTTP URLs
- **Space Isolation**: Files are organized by workspace/space ID
- **Direct Serving**: Frontend can directly load PDFs via public URLs in iframes

### Setup Instructions

1. **Create a Supabase Project**
   - Go to [supabase.com](https://supabase.com) and create a free account
   - Create a new project
   - Note your **Project URL** and **Anon/Public API Key** from Project Settings → API

2. **Create Storage Bucket**
   - Navigate to **Storage** in your Supabase dashboard
   - Click **New Bucket**
   - Name: `course-materials`
   - **Important**: Set bucket to **Public** (or configure appropriate policies)
   - This allows the frontend to access PDF URLs directly

3. **Set Environment Variables**
   ```bash
   # Windows PowerShell
   $env:SUPABASE_URL="https://your-project.supabase.co"
   $env:SUPABASE_KEY="your-anon-key-here"
   
   # Linux/Mac
   export SUPABASE_URL="https://your-project.supabase.co"
   export SUPABASE_KEY="your-anon-key-here"
   ```

### How It Works

#### Upload Flow
1. **Frontend** uploads PDF via `/api/upload` endpoint
2. **Backend** receives file and uploads to Supabase:
   ```
   Bucket: course-materials
   Path: space_{space_id}/{filename}
   Example: space_1/lecture_notes.pdf
   ```
3. **Public URL** is generated by Supabase:
   ```
   https://your-project.supabase.co/storage/v1/object/public/course-materials/space_1/lecture_notes.pdf
   ```
4. **RAG Processing**: The public URL is passed to the RAG system, which:
   - Downloads the PDF temporarily
   - Extracts and processes text
   - Generates embeddings
   - Cleans up temporary file
5. **Database Storage**: The public URL is saved to the database for future reference

#### Retrieval Flow
1. **Frontend** requests document via `/api/documents/{doc_id}/content`
2. **Backend** retrieves the Supabase public URL from database
3. **Frontend** displays PDF directly in iframe using the public URL
4. No backend file serving needed - Supabase handles it!

### File Organization Structure

```
course-materials/              # Supabase Bucket
├── space_1/                   # Workspace 1 (e.g., "CS101")
│   ├── lecture_01.pdf
│   ├── homework_assignment.pdf
│   └── textbook_chapter_3.pdf
├── space_2/                   # Workspace 2 (e.g., "Physics")
│   ├── lab_manual.pdf
│   └── lecture_notes.pdf
└── space_3/                   # Workspace 3
    └── syllabus.pdf
```

### Benefits of This Architecture

- ✅ **No Local Storage**: Files don't consume backend server disk space
- ✅ **Concurrent Access**: Multiple users can access files simultaneously
- ✅ **CDN Benefits**: Supabase uses CDN for faster global access
- ✅ **Backup**: Supabase handles backups automatically
- ✅ **Direct Serving**: Frontend loads PDFs directly from Supabase, reducing backend load
- ✅ **Space Isolation**: Easy to manage and query documents by workspace

### Cost Considerations

Supabase Free Tier includes:
- **1GB Storage** - Suitable for ~1000 typical lecture PDFs (assuming 1MB average)
- **2GB Bandwidth/month** - Sufficient for moderate usage
- **Unlimited API requests**

For production/larger deployments, consider Supabase Pro or custom storage solutions.

---

## Usage

### Web Interface
1. Navigate to `http://localhost:8000` in your browser
2. Upload a PDF document (lecture notes, textbook chapter, etc.)
3. Wait for processing to complete
4. Start asking questions about the document
5. Receive answers with source attribution

### API Endpoints

#### Upload Document
```http
POST /api/upload
Content-Type: multipart/form-data

file: <PDF file>
```

**Response:**
```json
{
  "status": "success",
  "message": "Knowledge Base Ready"
}
```

#### Query Document
```http
POST /api/chat
Content-Type: application/json

{
  "text": "What is the main topic of this document?"
}
```

**Response:**
```json
{
  "answer": "The main topic is...",
  "source_document": "lecture_notes.pdf",
  "top_chunk_page_content": "Context: ..."
}
```

### Python API

```python
from advanced_rag import AdvancedRAGSystem

# Initialize the system
rag = AdvancedRAGSystem()

# Process a document
docs = rag.load_and_process_pdf("path/to/document.pdf")
rag.build_index(docs)

# Query
result = rag.query("What are the key concepts?")
print(result["answer"])
print(f"Source: {result['source_document']}")
```

---

## RAG System Details

### Document Processing Pipeline

1. **PDF Extraction**: Fast text extraction using PyPDFLoader
2. **Chunking**: Recursive character splitting (800 chars, 150 overlap)
3. **Metadata Injection**: Source document tracking for attribution
4. **Contextual Enrichment**: Each chunk is contextualized using the broader document context
5. **Embedding**: High-quality embeddings via Google's text-embedding-004

### Retrieval Strategy

- **Hybrid Search**: Combines semantic (FAISS) and lexical (BM25) search with 50/50 weighting
- **Top-K Retrieval**: Fetches 15 candidate documents
- **Cross-Encoder Reranking**: Reranks candidates and selects top 5 most relevant
- **Source Tracking**: Maintains document provenance throughout the pipeline

### Configuration

Key parameters in `advanced_rag.py`:
```python
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-2.5-flash"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K_RETRIEVAL = 15  # Candidates for hybrid search
TOP_K_RERANK = 5      # Final docs sent to LLM
```

---

## Roadmap

### Phase 1: Core RAG (Current)
- [x] Advanced hybrid retrieval pipeline
- [x] Cross-encoder reranking
- [x] Contextual embeddings
- [x] Source attribution
- [x] Basic web interface

### Phase 2: Social Features (Planned)
- [ ] User authentication and profiles
- [ ] Course workspace creation
- [ ] Multi-student collaboration
- [ ] Query history and sharing
- [ ] Page-level threading system

### Phase 3: Collaboration Layer (Planned)
- [ ] Moderator roles and permissions
- [ ] Pull-request style contribution workflow
- [ ] Artifact sharing (bookmarks, annotations, summaries)
- [ ] Real-time collaboration features
- [ ] Activity feed per course space

### Phase 4: Document Intelligence (Planned)
- [ ] Document type detection (lecture/notes/textbook/transcript)
- [ ] Adaptive RAG strategies per document type
- [ ] Multi-document cross-referencing
- [ ] Automatic summary generation
- [ ] Concept extraction and linking

### Phase 5: Advanced Features (Future)
- [ ] Study group formation
- [ ] Flashcard generation from queries
- [ ] Practice question generation
- [ ] Progress tracking and analytics
- [ ] Mobile app

---

## Contributing

This is currently an experimental project. Contributions, ideas, and feedback are welcome!

### Development Setup
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## Project Structure

```
PythonProject2/
├── advanced_rag.py       # Core RAG system implementation
├── rag_server.py         # FastAPI web server
├── static/
│   └── index.html        # Web UI
├── __pycache__/          # Python cache files
└── README.md             # This file
```

---

## Configuration & Environment

### Required Environment Variables
- `GOOGLE_API_KEY`: Your Google API key for Gemini access
- `GROQ_API_KEY`: Your Groq API key for Llama 3.3 model access
- `SUPABASE_URL`: Your Supabase project URL (e.g., `https://xyz.supabase.co`)
- `SUPABASE_KEY`: Your Supabase anon/public API key

### Optional Configuration
Modify constants in `advanced_rag.py` to tune performance:
- Chunk sizes and overlap
- Number of retrieval candidates
- Reranking parameters
- LLM temperature settings

---

## Known Issues & Limitations

- **Single User**: Currently supports only one user at a time
- **In-Memory Storage**: Vector store is not persisted between sessions
- **No Multi-Document**: Only one document can be indexed at a time
- **Limited File Types**: Currently only supports PDF documents
- **No Authentication**: No user management or access control

---

## Performance

- **PDF Processing**: ~2-5 seconds for typical lecture notes (10-20 pages)
- **Query Response**: ~2-4 seconds including retrieval and generation
- **Embedding Model**: Google text-embedding-004 (1024 dimensions)
- **Context Window**: Up to 30,000 characters for contextual processing

---

## License

This project is currently unlicensed. License information will be added as the project matures.

---

## Acknowledgments

- Built with [LangChain](https://www.langchain.com/) for RAG orchestration
- Powered by [Google Gemini](https://ai.google.dev/) for LLM capabilities
- Uses [FAISS](https://github.com/facebookresearch/faiss) for efficient vector search
- Inspired by the need for better collaborative learning tools in higher education

---

## Contact

For questions, suggestions, or collaboration opportunities, please open an issue on GitHub.

---

<div align="center">

**Built with ❤️ for students, by students**

*Experimenting with the future of collaborative learning*

</div>


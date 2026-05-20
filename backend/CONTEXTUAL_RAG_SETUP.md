# LangGraph Contextual RAG Setup Guide

## Overview

This system implements a sophisticated **Contextual Retrieval-Augmented Generation (RAG)** pipeline that uses:

1. **LangGraph** - Workflow orchestration and chunk relationship mapping
2. **Ollama** - Local LLM for summarization and analysis (no API costs)
3. **Gemini API** - Global meaning extraction
4. **OpenAI Embeddings** - Vector representations
5. **PostgreSQL** - Persistent chunk storage with summaries and topics

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        DOCUMENT UPLOAD                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│   rag.py: Load & Split into Chunks                             │
│   - Load PDF/DOCX/TXT                                           │
│   - Split with overlap (1000 chars, 200 overlap)               │
│   - Store chunks in PostgreSQL DB                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│   FAISS Vector Store (for similarity search)                    │
│   - Quick retrieval of top-3 similar chunks                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│           USER QUERY → langgraph_contextual_rag.py             │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │   RETRIEVE   │→ │  SUMMARIZE   │→ │   ANALYZE    │        │
│  │   TOP-3      │  │  with Ollama │  │ RELATIONSHIPS│        │
│  │   CHUNKS     │  │              │  │ with LangGraph│        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                           │                   │                │
│                           ▼                   ▼                │
│  ┌──────────────────────────────────────────────────┐         │
│  │   GET GLOBAL MEANING with Gemini API             │         │
│  │   (How do these topics relate to the query?)    │         │
│  └──────────────────────┬───────────────────────────┘         │
│                         │                                      │
│                         ▼                                      │
│  ┌──────────────────────────────────────────────────┐         │
│  │   GENERATE ANSWER with Ollama (LOCAL)            │         │
│  │   - Uses summaries, topics, relationships       │         │
│  │   - Includes global meaning in context          │         │
│  │   - Completely local (no API for LLM)           │         │
│  └──────────────────────┬───────────────────────────┘         │
│                         │                                      │
│                         ▼                                      │
│  Return: Answer + Chunk Relationships + Debug Info            │
│                                                                 │
└─────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND DISPLAYS                            │
│  - AI Answer                                                    │
│  - Source chunks with topics                                   │
│  - Chunk relationships (LangGraph)                             │
│  - Relevance scores                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

You need:
1. **Ollama** - Local LLM server (https://ollama.ai)
2. **Gemini API Key** - From Google (https://makersuite.google.com)
3. **OpenAI API Key** - For embeddings only
4. **PostgreSQL** - Database
5. **Python 3.10+** - For backend

## Installation

### Step 1: Install Ollama

**Windows:**
1. Download from https://ollama.ai
2. Run installer (ollama-windows-amd64.exe)
3. Ollama will start automatically on http://localhost:11434

**macOS:**
```bash
brew install ollama
ollama serve
```

**Linux:**
```bash
curl https://ollama.ai/install.sh | sh
ollama serve
```

### Step 2: Pull a Local Model

Open terminal and run:

```bash
# Pull llama2 (default, 4GB)
ollama pull llama2

# OR Pull a faster model
ollama pull neural-chat

# OR Pull a high-quality model
ollama pull dolphin-mixtral

# OR Pull Gemma (fast and good)
ollama pull gemma
```

**Model Options:**
- `llama2` - Good quality, 4GB
- `neural-chat` - Fast, 4GB
- `dolphin-mixtral` - Better quality, 26GB
- `gemma` - Fast and good, 5GB
- `mistral` - Fast, 4GB

Check available models:
```bash
ollama list
```

### Step 3: Get API Keys

**Gemini API Key:**
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API key"
3. Copy the key

**OpenAI API Key:**
1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy the key

### Step 4: Update Configuration

Edit `backend/.env`:

```env
# Existing settings
OPENAI_API_KEY=sk-your-openai-key-here

# NEW: Ollama Configuration
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama2  # Change to your model

# NEW: Gemini Configuration
GEMINI_API_KEY=your-gemini-key-here

# NEW: Contextual RAG Settings
K_CHUNKS_CONTEXTUAL=3
CHUNK_SUMMARIZATION_ENABLED=True
CHUNK_RELATIONSHIP_ANALYSIS_ENABLED=True
GEMINI_GLOBAL_CONTEXT_ENABLED=True
```

### Step 5: Install Dependencies

```powershell
cd backend
pip install -r requirements.txt
```

This installs:
- `langgraph` - Workflow orchestration
- `google-generativeai` - Gemini API
- `requests` - HTTP calls to Ollama
- Updated `langchain` packages

### Step 6: Run the System

**Terminal 1 - Ollama Server:**
```bash
ollama serve
```

**Terminal 2 - PostgreSQL:**
```bash
# Windows/Docker: Make sure PostgreSQL is running
# If using Docker:
docker run -p 5432:5432 -e POSTGRES_PASSWORD=password postgres
```

**Terminal 3 - Backend:**
```powershell
cd backend
python main.py
```

**Terminal 4 - Frontend:**
```bash
# In a new terminal, navigate to frontend directory
python -m http.server 8000
# Or use VS Code Live Server extension
```

## How It Works - Step by Step

### 1. Document Upload

When you upload a PDF/DOCX/TXT:

```
Frontend: POST /api/documents/upload
           ↓
Backend (documents.py):
  - Save file to disk
  - Create Document DB record
  - Call process_document_chunks_contextual()
      ↓
rag.py:
  - Load file (PyPDF, Docx2txt, or read txt)
  - Split into chunks (1000 chars, 200 overlap)
  - Create DocumentChunk records in DB
  - Build FAISS vector store
  - Return success
```

### 2. User Query

When user sends a question:

```
Frontend: POST /api/messages/send
           ↓
messages.py:
  - Get user query
  - Call langgraph_contextual_rag.retrieve_similar_chunks()
      ↓
langgraph_contextual_rag.py:
  [1] RETRIEVE:
      - Embed query with OpenAI
      - Search FAISS for top-3 chunks
      
  [2] SUMMARIZE (LangGraph Node 1):
      - For each chunk without summary:
        - Call Ollama with chunk text
        - Get summary (1-2 sentences)
      - For each chunk without topic:
        - Call Ollama to extract topic (1-3 words)
      
  [3] BUILD RELATIONSHIPS (LangGraph Node 2):
      - Analyze topic overlap between chunks
      - Analyze content overlap (word similarity)
      - Build graph of relationships
      - Example: Chunk-1 (Finance) relates to Chunk-2 (Payments)
      
  [4] GLOBAL CONTEXT (LangGraph Node 3):
      - Collect all topics: ["Finance", "Payments", "Terms"]
      - Call Gemini API with:
        Topics: Finance, Payments, Terms
        Query: "What are payment terms?"
      - Gemini returns: "In financial documents, payment terms refer to..."
      
  [5] GENERATE ANSWER (LangGraph Node 4):
      - Build prompt with:
        * Chunk summaries
        * Chunk relationships (graph)
        * Global meaning from Gemini
        * User query
      - Call Ollama (LOCAL - no API cost)
      - Get final answer
      
Result: Answer + Chunk Relationships + Global Meaning
           ↓
messages.py: Store in DB, return to frontend
```

### 3. Database Storage

**Chunks with Metadata:**
```sql
document_chunks:
  - chunk_id (PK)
  - chunk_text (full text)
  - doc_id (FK to documents)
  - summary (generated by Ollama)
  - topic (extracted by Ollama)
  - processed_at (timestamp)

chunk_embeddings:
  - embedding_id (PK)
  - chunk_id (FK)
  - embedding (vector for chunk)

chunk_summary_embeddings:  # NEW
  - summary_embedding_id (PK)
  - chunk_id (FK)
  - summary_embedding (vector for summary)
```

## Configuration Options

**In `.env`:**

### LangChain
```env
CHUNK_SIZE=1000              # Chunk length in characters
CHUNK_OVERLAP=200            # Overlap to prevent splitting mid-sentence
K_DOCUMENTS=5                # For basic RAG (not contextual)
```

### Contextual RAG
```env
K_CHUNKS_CONTEXTUAL=3        # How many chunks to retrieve
CHUNK_SUMMARIZATION_ENABLED=True      # Use Ollama summaries
CHUNK_RELATIONSHIP_ANALYSIS_ENABLED=True  # Build LangGraph
GEMINI_GLOBAL_CONTEXT_ENABLED=True   # Use Gemini for context
```

### Ollama
```env
OLLAMA_API_URL=http://localhost:11434
OLLAMA_MODEL=llama2          # Change this to your model
```

### APIs
```env
OPENAI_API_KEY=sk-...        # For embeddings only
GEMINI_API_KEY=...           # For global meaning
```

## Performance Tips

### 1. Chunk Size
- **Smaller (500):** Fast retrieval, less context
- **Default (1000):** Good balance
- **Larger (2000):** More context, slower

### 2. K_CHUNKS_CONTEXTUAL
- **1-2:** Very specific answers
- **Default (3):** Good for most cases
- **5+:** More context, slower

### 3. Ollama Model Selection
- `llama2` (4GB) - Good quality, slower
- `neural-chat` (4GB) - Fast, okay quality
- `gemma` (5GB) - Fast and good
- `dolphin-mixtral` (26GB) - Best quality, slow

### 4. Optimization
```env
# For speed (use fast model)
OLLAMA_MODEL=neural-chat
K_CHUNKS_CONTEXTUAL=2

# For quality (use good model)
OLLAMA_MODEL=dolphin-mixtral
K_CHUNKS_CONTEXTUAL=5
```

## Troubleshooting

### Error: "Connection refused: http://localhost:11434"
**Solution:** Start Ollama
```bash
ollama serve
```

### Error: "model 'llama2' not found"
**Solution:** Pull the model
```bash
ollama pull llama2
```

### Error: "Gemini API key not configured"
**Solution:** Get key from https://makersuite.google.com/app/apikey and add to `.env`

### Error: "No relevant chunks found"
**Solution:**
- Try a different query
- Make sure document was uploaded
- Check if chunks were processed

### Slow Response Time
**Solution:**
- Use faster model: `neural-chat` or `gemma`
- Reduce `K_CHUNKS_CONTEXTUAL` to 2
- Increase chunk size to 1500

### Memory Usage High
**Solution:**
- Use smaller model: `neural-chat` instead of `dolphin-mixtral`
- Close other applications
- Reduce `CHUNK_SIZE`

## API Costs

**With this setup:**

| Component | Cost | Notes |
|-----------|------|-------|
| Ollama | $0 | Local, no API |
| OpenAI Embeddings | ~$0.02 per 1M tokens | For embeddings only |
| Gemini API | Free tier | Or paid for high volume |
| PostgreSQL | $0 | Self-hosted |
| **Total** | **Very Low** | ~$0.001-0.01 per query |

**Compared to alternatives:**

| Service | Cost per Query |
|---------|---|
| ChatGPT API | $0.01-0.05 |
| This system | $0.001-0.01 |
| 100% Local LLM | $0 (but lower quality) |

## Database Initialization

If you need to update database schema for new fields:

```sql
-- Add to existing document_chunks table
ALTER TABLE document_chunks
ADD COLUMN summary TEXT,
ADD COLUMN topic VARCHAR(255),
ADD COLUMN processed_at TIMESTAMP;

-- Create new table for summary embeddings
CREATE TABLE chunk_summary_embeddings (
    summary_embedding_id SERIAL PRIMARY KEY,
    chunk_id INTEGER NOT NULL UNIQUE REFERENCES document_chunks(chunk_id) ON DELETE CASCADE,
    summary_embedding BYTEA NOT NULL,
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for faster lookups
CREATE INDEX idx_chunk_topic ON document_chunks(topic);
CREATE INDEX idx_chunk_processed ON document_chunks(processed_at);
```

Or let SQLAlchemy create tables automatically:
```python
# In main.py, on startup:
Base.metadata.create_all(bind=engine)  # Includes new models
```

## Example Workflow

```
1. User uploads "contract.pdf" (4 pages)
   → System loads PDF
   → Splits into 23 chunks
   → Stores in DB
   → Creates FAISS vector store

2. User asks: "What are the payment terms?"
   → Embeds query with OpenAI
   → Searches FAISS, finds top-3 chunks:
     * Chunk-5: "Payments...", relevance: 0.92
     * Chunk-12: "Invoice schedule...", relevance: 0.87
     * Chunk-3: "Terms of service...", relevance: 0.82
   
   → Summarizes each chunk with Ollama:
     * Chunk-5: "Document specifies payment due within 30 days of invoice."
     * Chunk-12: "Invoices issued monthly on the last day."
     * Chunk-3: "Standard terms apply unless otherwise negotiated."
   
   → Extracts topics:
     * Chunk-5: "Payment Terms"
     * Chunk-12: "Invoice Schedule"
     * Chunk-3: "Contract Terms"
   
   → Builds relationship graph:
     * Payment Terms ──→ Invoice Schedule (both about money)
     * Contract Terms ──→ Payment Terms (contract governs payments)
   
   → Gets global meaning with Gemini:
     "Payment terms refer to the agreed-upon schedule and conditions for 
     paying invoices. In contracts, they specify when payment is due, 
     methods accepted, and any penalties for late payment."
   
   → Generates answer with Ollama:
     "Based on the document:
     
     The payment terms require payment within 30 days of invoice 
     (specified in Chunk-5). Invoices are issued monthly (Chunk-12), 
     and all terms are governed by the standard contract terms 
     (Chunk-3) unless negotiated otherwise.
     
     [Chunk Relationships: Payment Terms connects Invoice Schedule 
     and Contract Terms]
     
     [Global Context: Payment terms define the payment schedule and 
     conditions in financial agreements]"
   
   → Frontend displays answer with sources and relationship graph
```

## Next Steps

1. **Start Ollama server**
2. **Update `.env` with API keys**
3. **Install dependencies: `pip install -r requirements.txt`**
4. **Run backend: `python main.py`**
5. **Upload a document**
6. **Ask questions!**

The system will automatically:
- Summarize chunks with Ollama
- Extract topics with Ollama
- Build relationship graphs with LangGraph
- Get global context with Gemini
- Generate answers with Ollama

All without expensive API calls for the LLM!

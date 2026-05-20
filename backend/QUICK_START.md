# LangGraph Contextual RAG - Quick Start

## What You're Getting

A sophisticated contextual RAG system that:
- ✅ Splits documents into chunks
- ✅ Summarizes chunks with **local Ollama** (no API costs)
- ✅ Extracts topics with **local Ollama**
- ✅ Builds chunk relationship graphs with **LangGraph**
- ✅ Gets global context with **Gemini API**
- ✅ Generates final answers with **local Ollama**

**Cost:** ~$0.001-0.01 per query (embeddings only)
**Privacy:** All LLM processing is local (only Gemini for global meaning)

---

## 5-Minute Setup

### 1. Install Ollama
Download: https://ollama.ai

```bash
ollama pull llama2  # or: gemma, neural-chat, dolphin-mixtral
```

### 2. Get API Keys
- **Gemini:** https://makersuite.google.com/app/apikey
- **OpenAI:** https://platform.openai.com/api-keys

### 3. Update Configuration
Edit `backend/.env`:
```env
OPENAI_API_KEY=sk-your-key
GEMINI_API_KEY=your-gemini-key
OLLAMA_MODEL=llama2
OLLAMA_API_URL=http://localhost:11434
```

### 4. Install & Run

```powershell
# Terminal 1: Ollama
ollama serve

# Terminal 2: PostgreSQL (if needed)
# Make sure it's running on localhost:5432

# Terminal 3: Backend
cd backend
pip install -r requirements.txt
python main.py

# Terminal 4: Frontend
python -m http.server 8000
```

### 5. Use It!
1. Open http://localhost:8000
2. Login/Signup
3. Upload a document
4. Ask questions!

---

## Key Files Created

| File | Purpose |
|------|---------|
| `langgraph_contextual_rag.py` | LangGraph workflow + Ollama integration |
| `CONTEXTUAL_RAG_SETUP.md` | Detailed setup guide |
| `LANGCHAIN_GUIDE.txt` | Basic LangChain overview |
| `contextual_rag_migration.sql` | Database schema updates |

## Key Files Modified

| File | Changes |
|------|---------|
| `models.py` | Added `summary`, `topic`, `processed_at` to DocumentChunk |
| `messages.py` | Now uses contextual RAG instead of basic RAG |
| `documents.py` | Calls contextual processing on upload |
| `rag.py` | Added `process_document_chunks_contextual()` |
| `requirements.txt` | Added langgraph, google-generativeai |
| `.env` | Added Ollama, Gemini, contextual settings |

---

## How It Works (Simple Version)

```
Upload Document
    ↓
Split into chunks + store in DB
    ↓
User asks question
    ↓
[LangGraph Workflow]
├─ Retrieve top-3 chunks from FAISS
├─ Summarize with local Ollama
├─ Extract topics with local Ollama
├─ Build relationship graph
├─ Get global context with Gemini
└─ Generate answer with local Ollama
    ↓
Return answer + relationships + sources
```

---

## Configuration Examples

### Speed (Fast Responses)
```env
OLLAMA_MODEL=neural-chat
K_CHUNKS_CONTEXTUAL=2
CHUNK_SIZE=800
```

### Quality (Better Answers)
```env
OLLAMA_MODEL=dolphin-mixtral
K_CHUNKS_CONTEXTUAL=5
CHUNK_SIZE=1200
```

### Balanced (Recommended)
```env
OLLAMA_MODEL=llama2        # or gemma
K_CHUNKS_CONTEXTUAL=3
CHUNK_SIZE=1000
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Connection refused: 11434" | Run `ollama serve` |
| "Model not found" | Run `ollama pull llama2` |
| "Slow responses" | Use `neural-chat` model |
| "No chunks found" | Make sure document uploaded |
| "Gemini error" | Check API key in `.env` |

---

## API Endpoints

### Upload Document
```
POST /api/documents/upload
- Automatically processes chunks
- Creates summaries on demand
- Stores in DB
```

### Send Message
```
POST /api/messages/send
- Retrieves top-3 chunks
- Runs LangGraph workflow
- Returns answer + sources
```

---

## Cost Breakdown

**Per Query:**
- Ollama (local): $0.00
- OpenAI Embeddings: $0.00002
- Gemini API: Free (standard tier)
- **Total: ~$0.00002**

**vs GPT-4 API: $0.05-0.10 per query**

---

## Next Steps

1. ✅ Install Ollama and pull a model
2. ✅ Get API keys (Gemini, OpenAI)
3. ✅ Update `.env`
4. ✅ Install dependencies
5. ✅ Run all services
6. ✅ Test with a document

---

## Features Overview

### Chunk Summarization
```
Original: "Payment terms are defined as the period between invoice
          issuance and when payment is due. In this agreement, payment
          must be made within 30 days of invoice date..."

Summary: "Payments due within 30 days of invoice."
```

### Topic Extraction
```
Chunk: "In accordance with standard industry practices, all payment
       disputes must be resolved within 15 business days..."

Topic: "Dispute Resolution"
```

### Relationship Mapping
```
Chunk-1: Payment Terms
    ↓ (related_to) ↓
Chunk-3: Invoice Schedule
    ↓ (related_to) ↓
Chunk-5: Late Payment Penalties
```

### Global Context
```
Query: "What are the payment terms?"

Gemini: "Payment terms refer to the agreed-upon timeframe and 
        conditions for paying invoices in a contract. They typically 
        specify the due date, payment method, and any penalties for 
        late payment."
```

### Final Answer
```
"Based on the document, payment terms require payment within 
30 days of invoice issuance (as detailed in Chunk-1). Invoices 
are issued monthly (Chunk-3), and late payments incur a 1.5% 
monthly penalty (Chunk-5).

[Chunk Relationships: Payment Terms connects Invoice Schedule 
and Late Payment Penalties]

[Global Context: Payment terms define when and how invoices 
must be paid]"
```

---

## Advanced Configuration

### Enable/Disable Features
```env
CHUNK_SUMMARIZATION_ENABLED=True
CHUNK_RELATIONSHIP_ANALYSIS_ENABLED=True
GEMINI_GLOBAL_CONTEXT_ENABLED=True
```

### Performance Tuning
```env
# More chunks = better context, slower response
K_CHUNKS_CONTEXTUAL=3

# Larger chunks = more context, fewer chunks
CHUNK_SIZE=1000

# More overlap = better continuity
CHUNK_OVERLAP=200
```

### Model Selection
```
llama2           → Good quality, moderate speed
gemma            → Fast and good quality (recommended)
neural-chat      → Very fast, okay quality
dolphin-mixtral  → Excellent quality, slow
```

---

## Database Updates

Run migration to add new columns:

```sql
-- Run in PostgreSQL
psql -U postgres -d document_rag_db -f database/contextual_rag_migration.sql
```

Or let SQLAlchemy handle it automatically when you start the app.

---

## Support & Debugging

**Check logs in terminal:**
```
[Contextual RAG] Processing query...
[Ollama] Summary generated: ...
[LangGraph] Built graph: 3 nodes, 2 edges
[Gemini] Global meaning generated
```

**Test Ollama connection:**
```bash
curl http://localhost:11434/api/tags
```

**Test OpenAI embeddings:**
```python
from openai import OpenAI
client = OpenAI(api_key="your-key")
response = client.embeddings.create(input="test", model="text-embedding-3-small")
print(response.data[0].embedding[:5])  # Should print 5 numbers
```

---

## What's Different from Basic RAG?

| Feature | Basic RAG | Contextual RAG |
|---------|-----------|---|
| Retrieval | Embedding similarity | Embedding similarity + FAISS |
| Summarization | None | ✅ Ollama summaries |
| Topic Extraction | None | ✅ Ollama topics |
| Relationships | None | ✅ LangGraph analysis |
| Global Context | None | ✅ Gemini API |
| Cost per Query | $0.01-0.05 | $0.00002 |
| Speed | Fast | Moderate |
| Answer Quality | Good | Excellent |

---

## You're All Set! 🚀

Upload a document and start asking questions. The system will:
1. Automatically summarize chunks
2. Extract key topics
3. Map chunk relationships
4. Understand global context
5. Generate comprehensive answers

All with minimal API costs and maximum privacy!

from langchain.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
import shutil

load_dotenv()

# Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
K_DOCUMENTS = int(os.getenv("K_DOCUMENTS", 5))

# Initialize local embedding model
print("[RAG] Loading embedding model:", EMBEDDING_MODEL)
embedding_model = SentenceTransformer(EMBEDDING_MODEL)
print("[RAG] Embedding model loaded (local, no API)")

# Vector store directory
VECTOR_STORE_DIR = "vector_stores"
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

# ===== DOCUMENT LOADERS =====
def load_pdf(file_path: str):
    """Load PDF file using PyPDFLoader"""
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
        return documents
    except Exception as e:
        print(f"Error loading PDF: {str(e)}")
        return []

def load_docx(file_path: str):
    """Load DOCX file using Docx2txtLoader"""
    try:
        loader = Docx2txtLoader(file_path)
        documents = loader.load()
        return documents
    except Exception as e:
        print(f"Error loading DOCX: {str(e)}")
        return []

def load_txt(file_path: str):
    """Load TXT file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        from langchain.schema import Document
        return [Document(page_content=content, metadata={"source": file_path})]
    except Exception as e:
        print(f"Error loading TXT: {str(e)}")
        return []

# ===== DOCUMENT LOADING DISPATCHER =====
def load_document(file_path: str, file_type: str):
    """Load document based on file type"""
    print(f"Loading {file_type} file: {file_path}")
    
    if file_type == "pdf":
        return load_pdf(file_path)
    elif file_type == "docx":
        return load_docx(file_path)
    elif file_type == "txt":
        return load_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

# ===== TEXT SPLITTING =====
def split_documents(documents: list):
    """
    Split documents into chunks for embedding
    Uses recursive character splitter for better semantic chunks
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""]
    )
    
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} chunks from documents")
    return chunks

# ===== EMBEDDINGS (LOCAL - NO API) =====
def get_embeddings():
    """Get local embeddings using sentence-transformers"""
    # Create a simple wrapper for sentence-transformers to work with FAISS
    class LocalEmbeddings:
        def __init__(self, model):
            self.model = model
        
        def embed_documents(self, texts):
            embeddings = []
            for text in texts:
                embedding = self.model.encode(text[:512], convert_to_tensor=False)
                embeddings.append(embedding.tolist())
            return embeddings
        
        def embed_query(self, text):
            embedding = self.model.encode(text[:512], convert_to_tensor=False)
            return embedding.tolist()
    
    return LocalEmbeddings(embedding_model)

# ===== VECTOR STORE =====
def create_vector_store(chunks: list, user_id: int, doc_id: int):
    """
    Create FAISS vector store from document chunks
    Stores vector store for reuse
    """
    embeddings = get_embeddings()
    
    # Create FAISS vector store
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    # Save vector store
    store_path = os.path.join(VECTOR_STORE_DIR, f"user_{user_id}_doc_{doc_id}")
    vector_store.save_local(store_path)
    
    print(f"Vector store saved to {store_path}")
    return vector_store

def load_vector_store(user_id: int, doc_id: int):
    """Load existing vector store"""
    embeddings = get_embeddings()
    store_path = os.path.join(VECTOR_STORE_DIR, f"user_{user_id}_doc_{doc_id}")
    
    try:
        vector_store = FAISS.load_local(store_path, embeddings)
        return vector_store
    except Exception as e:
        print(f"Error loading vector store: {str(e)}")
        return None

def delete_vector_store(user_id: int, doc_id: int):
    """Delete vector store when document is deleted"""
    store_path = os.path.join(VECTOR_STORE_DIR, f"user_{user_id}_doc_{doc_id}")
    
    try:
        if os.path.exists(store_path):
            shutil.rmtree(store_path)
            print(f"Vector store deleted: {store_path}")
    except Exception as e:
        print(f"Error deleting vector store: {str(e)}")

# ===== DEPRECATED: RAG CHAIN (Use langgraph_contextual_rag.py instead) =====
# The create_rag_chain function has been removed as it used OpenAI.
# Use langgraph_contextual_rag.py for contextual RAG with local Ollama + Gemini.

def answer_question(query: str, user_id: int, doc_id: int):
    """
    DEPRECATED: Use langgraph_contextual_rag.answer_question_contextual() instead
    
    This function is kept for backward compatibility only.
    It does not generate answers, only returns error.
    """
    return {
        "error": "Basic RAG is deprecated. Use contextual RAG from langgraph_contextual_rag.py",
        "response": None,
        "sources": [],
        "note": "Call langgraph_contextual_rag.answer_question_contextual() instead"
    }

# ===== DOCUMENT PROCESSING PIPELINE =====
def process_document_for_rag(file_path: str, file_type: str, user_id: int, doc_id: int):
    """
    Complete pipeline: Load → Split → Embed → Store
    """
    
    try:
        print(f"Starting RAG processing for {file_path}")
        
        # 1. Load document
        documents = load_document(file_path, file_type)
        if not documents:
            return {"error": "Failed to load document"}
        
        print(f"Loaded {len(documents)} pages/sections")
        
        # 2. Split into chunks
        chunks = split_documents(documents)
        if not chunks:
            return {"error": "Failed to split document"}
        
        print(f"Created {len(chunks)} chunks")
        
        # 3. Create vector store and embeddings
        vector_store = create_vector_store(chunks, user_id, doc_id)
        
        print(f"Vector store created with {len(chunks)} embeddings")
        
        return {
            "success": True,
            "chunks": len(chunks),
            "message": "Document indexed successfully for RAG"
        }
    
    except Exception as e:
        print(f"Error in RAG processing: {str(e)}")
        return {"error": str(e)}

# ===== CONTEXTUAL RAG INTEGRATION =====
def process_document_chunks_contextual(
    file_path: str,
    file_type: str,
    user_id: int,
    doc_id: int,
    db = None
):
    """
    Process document chunks with contextual RAG:
    - Load document
    - Split into chunks
    - Store in database
    - Summarize and extract topics with Ollama (background task)
    
    Args:
        file_path: Path to document file
        file_type: File type (pdf, docx, txt)
        user_id: User ID
        doc_id: Document ID
        db: Database session (optional)
    
    Returns:
        Result dict with chunk information
    """
    
    try:
        print(f"\n[Contextual Processing] Starting for doc_id={doc_id}")
        
        # 1. Load document
        documents = load_document(file_path, file_type)
        if not documents:
            return {"error": "Failed to load document"}
        
        print(f"[Contextual Processing] Loaded {len(documents)} pages")
        
        # 2. Split into chunks
        chunks = split_documents(documents)
        if not chunks:
            return {"error": "Failed to split document"}
        
        print(f"[Contextual Processing] Created {len(chunks)} chunks")
        
        # 3. Store chunks in database (with Ollama processing in background)
        # Note: Actual Ollama processing happens in langgraph_contextual_rag
        # when chunks are retrieved (lazy evaluation)
        
        if db:
            from models import DocumentChunk, DocumentSection
            
            # Create default section if needed
            default_section = db.query(DocumentSection).filter(
                DocumentSection.doc_id == doc_id,
                DocumentSection.section_title == "Main Content"
            ).first()
            
            if not default_section:
                default_section = DocumentSection(
                    doc_id=doc_id,
                    section_title="Main Content",
                    section_number=1
                )
                db.add(default_section)
                db.flush()  # Get the section_id without committing
            
            # Store chunks
            for i, chunk in enumerate(chunks):
                db_chunk = DocumentChunk(
                    doc_id=doc_id,
                    section_id=default_section.section_id,
                    chunk_number=i + 1,
                    chunk_text=chunk.page_content,
                    summary=None,  # Will be generated on demand by langgraph_contextual_rag
                    topic=None  # Will be generated on demand
                )
                db.add(db_chunk)
            
            db.commit()
            print(f"[Contextual Processing] Stored {len(chunks)} chunks in database")
        
        # 4. Create vector store for quick similarity search
        vector_store = create_vector_store(chunks, user_id, doc_id)
        
        print(f"[Contextual Processing] Complete! Chunks ready for contextual analysis")
        
        return {
            "success": True,
            "chunks": len(chunks),
            "message": "Document chunks stored. Ready for contextual RAG analysis.",
            "processing_mode": "contextual_lazy"  # Summaries generated on query
        }
        
    except Exception as e:
        print(f"[Contextual Processing] Error: {str(e)}")
        return {"error": str(e)}


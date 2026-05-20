from langchain.document_loaders import PyPDFLoader
from langchain_community.document_loaders import Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv
import shutil

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 200))
K_DOCUMENTS = int(os.getenv("K_DOCUMENTS", 5))

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

# ===== EMBEDDINGS =====
def get_embeddings():
    """Get OpenAI embeddings"""
    embeddings = OpenAIEmbeddings(
        openai_api_key=OPENAI_API_KEY,
        model="text-embedding-3-small"
    )
    return embeddings

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

# ===== RAG CHAIN =====
def create_rag_chain(vector_store):
    """
    Create RAG chain for question answering
    Combines retriever with LLM
    """
    
    # Initialize LLM
    llm = ChatOpenAI(
        openai_api_key=OPENAI_API_KEY,
        model_name=OPENAI_MODEL,
        temperature=0.7,
        max_tokens=1000
    )
    
    # Create custom prompt
    prompt_template = """You are a helpful assistant answering questions about documents.
Use the following pieces of context to answer the question.
If you don't know the answer based on the context, say "I don't have enough information to answer that."

Context:
{context}

Question: {question}

Answer:"""
    
    PROMPT = PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )
    
    # Create retrieval chain
    chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vector_store.as_retriever(search_kwargs={"k": K_DOCUMENTS}),
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True
    )
    
    return chain

# ===== QUESTION ANSWERING =====
def answer_question(query: str, user_id: int, doc_id: int):
    """
    Answer a question using RAG
    
    Args:
        query: User's question
        user_id: User ID
        doc_id: Document ID to search in
    
    Returns:
        response: AI's answer
        source_documents: Retrieved documents
    """
    
    try:
        # Load vector store
        vector_store = load_vector_store(user_id, doc_id)
        
        if not vector_store:
            return {
                "error": "Vector store not found. Document may not be indexed yet.",
                "response": None,
                "sources": []
            }
        
        # Create RAG chain
        chain = create_rag_chain(vector_store)
        
        # Ask question
        result = chain({"query": query})
        
        return {
            "response": result.get("result", ""),
            "sources": [
                {
                    "content": doc.page_content[:500],  # First 500 chars
                    "metadata": doc.metadata
                }
                for doc in result.get("source_documents", [])
            ]
        }
    
    except Exception as e:
        print(f"Error answering question: {str(e)}")
        return {
            "error": str(e),
            "response": None,
            "sources": []
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


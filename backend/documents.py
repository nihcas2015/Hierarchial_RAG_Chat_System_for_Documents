from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from schemas import DocumentResponse, FileUploadResponse
from models import User, Document
from database import get_db
from utils import verify_token
from rag import process_document_chunks_contextual, delete_vector_store
import os
import shutil
from datetime import datetime

router = APIRouter(prefix="/api", tags=["documents"])

# Allowed file extensions
ALLOWED_EXTENSIONS = {"pdf", "txt", "doc", "docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
UPLOAD_DIR = "uploads"

# Create uploads directory if it doesn't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ===== HELPER FUNCTION: GET CURRENT USER =====
def get_current_user(authorization: str = None, db: Session = None) -> User:
    """Extract user from JWT token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid token"
        )
    
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    
    if "error" in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=payload["error"]
        )
    
    user = db.query(User).filter(User.user_id == payload["user_id"]).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user

# ===== UPLOAD DOCUMENT ENDPOINT =====
@router.post("/documents/upload", response_model=FileUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    authorization: str = None,
    db: Session = Depends(get_db)
):
    """
    Upload a document
    
    Request:
        - file: Document file (pdf, txt, doc, docx)
    
    Headers:
        - Authorization: Bearer <token>
    
    Response:
        - success: True/False
        - message: Upload status
        - doc_id: Document ID
        - file_name: File name
    """
    
    try:
        # Authenticate user
        user = get_current_user(authorization, db)
        
        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No file provided"
            )
        
        # Check file extension
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Check file size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File too large. Maximum 10MB"
            )
        
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{user.user_id}_{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create document record in database
        document = Document(
            user_id=user.user_id,
            file_name=file.filename,
            file_path=file_path,
            content_type=file.content_type
        )
        
        db.add(document)
        db.commit()
        db.refresh(document)
        
        # ===== Process document for Contextual RAG (LangGraph + Ollama + Gemini) =====
        # Extract file type from extension
        file_ext = file.filename.split(".")[-1].lower()
        
        # Process with contextual RAG
        # Note: Ollama summaries and topics are generated on-demand when queried
        processing_result = process_document_chunks_contextual(
            file_path,
            file_ext,
            user.user_id,
            document.doc_id,
            db=db  # Pass session for storing chunks
        )
        
        if "error" in processing_result:
            print(f"[Documents] Processing error: {processing_result['error']}")
            # Continue anyway - document is stored, just not fully indexed
        else:
            print(f"[Documents] Processing successful: {processing_result.get('message')}")
        
        return FileUploadResponse(
            success=True,
            message="Document uploaded successfully. Ready for contextual analysis.",
            doc_id=document.doc_id,
            file_name=file.filename
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Upload failed"
        )

# ===== GET ALL DOCUMENTS ENDPOINT =====
@router.get("/documents")
async def get_documents(
    authorization: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all documents for the current user
    
    Headers:
        - Authorization: Bearer <token>
    
    Response:
        - success: True/False
        - documents: List of documents
    """
    
    try:
        # Authenticate user
        user = get_current_user(authorization, db)
        
        # Get all documents for this user
        documents = db.query(Document).filter(Document.user_id == user.user_id).all()
        
        documents_data = [
            {
                "doc_id": doc.doc_id,
                "file_name": doc.file_name,
                "content_type": doc.content_type,
                "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None
            }
            for doc in documents
        ]
        
        return {
            "success": True,
            "documents": documents_data
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents"
        )

# ===== DELETE DOCUMENT ENDPOINT =====
@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: int,
    authorization: str = None,
    db: Session = Depends(get_db)
):
    """
    Delete a document
    
    Path Params:
        - doc_id: Document ID
    
    Headers:
        - Authorization: Bearer <token>
    
    Response:
        - success: True/False
        - message: Status message
    """
    
    try:
        # Authenticate user
        user = get_current_user(authorization, db)
        
        # Get document
        document = db.query(Document).filter(
            Document.doc_id == doc_id,
            Document.user_id == user.user_id
        ).first()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Delete file
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        
        # Delete vector store for RAG
        delete_vector_store(user.user_id, document.doc_id)
        
        # Delete from database
        db.delete(document)
        db.commit()
        
        return {
            "success": True,
            "message": "Document deleted successfully"
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document"
        )

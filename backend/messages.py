from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas import ChatMessageCreate, ChatResponse, ConversationResponse
from models import User, ChatMessage, Conversation, Document, DocumentChunk
from database import get_db
from utils import verify_token
from langgraph_contextual_rag import answer_question_contextual, retrieve_similar_chunks, ChunkState
import json

router = APIRouter(prefix="/api", tags=["messages"])

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

# ===== SEND MESSAGE ENDPOINT =====
@router.post("/messages/send", response_model=ChatResponse)
async def send_message(
    request: ChatMessageCreate,
    conversation_id: int = None,
    authorization: str = None,
    db: Session = Depends(get_db)
):
    """
    Send a message in a conversation
    
    Request:
        - message: User's message
    
    Query Params:
        - conversation_id: Existing conversation (optional)
    
    Headers:
        - Authorization: Bearer <token>
    
    Response:
        - success: True/False
        - response: AI response
        - message_id: Message ID
    """
    
    try:
        # Authenticate user
        user = get_current_user(authorization, db)
        
        # Create or get conversation
        if conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.conversation_id == conversation_id,
                Conversation.user_id == user.user_id
            ).first()
            
            if not conversation:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )
        else:
            # Create new conversation
            conversation = Conversation(
                user_id=user.user_id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        # Create chat message
        chat_message = ChatMessage(
            conversation_id=conversation.conversation_id,
            user_message=request.message,
            assistant_response="",  # Will be updated by RAG system
            relevant_chunks=""
        )
        
        db.add(chat_message)
        db.commit()
        db.refresh(chat_message)
        
        # ===== Use Contextual RAG (LangGraph + Ollama + Gemini) =====
        ai_response = ""
        relevant_chunks = ""
        debug_info = {}
        
        if conversation.doc_id:
            # User has selected a document, use contextual RAG
            try:
                # Step 1: Retrieve similar chunks
                print(f"\n[Messages] Retrieving similar chunks for doc_id={conversation.doc_id}")
                retrieved_chunks = retrieve_similar_chunks(
                    request.message,
                    db,
                    conversation.doc_id,
                    top_k=3
                )
                
                if not retrieved_chunks:
                    ai_response = "No relevant chunks found in the document. Please try a different question."
                else:
                    # Step 2: Use contextual RAG (LangGraph workflow)
                    print(f"[Messages] Running contextual RAG workflow...")
                    rag_result = answer_question_contextual(request.message, retrieved_chunks)
                    
                    ai_response = rag_result.get("answer", "No response generated")
                    debug_info = rag_result.get("debug_info", {})
                    
                    # Store relevant sources
                    sources = rag_result.get("sources", [])
                    if sources:
                        relevant_chunks = json.dumps([
                            {
                                "topic": s.get("topic", ""),
                                "summary": s.get("summary", ""),
                                "relevance": s.get("relevance", 0)
                            }
                            for s in sources
                        ])
                    
                    # Add chunk relationships for debugging
                    relationships = rag_result.get("chunk_relationships", {})
                    if relationships:
                        debug_info["chunk_graph"] = relationships
                    
                    if rag_result.get("global_meaning"):
                        debug_info["global_meaning"] = rag_result["global_meaning"]
                    
            except Exception as e:
                print(f"[Messages] Contextual RAG Error: {str(e)}")
                ai_response = f"Error in contextual RAG: {str(e)}"
        else:
            # No document selected, use general response
            ai_response = f"Hello! I'm ready to help you. Please upload a document first, then ask questions about it.\n\nYour question: {request.message}"
        
        # Update message with AI response and sources
        chat_message.assistant_response = ai_response
        chat_message.relevant_chunks = relevant_chunks
        db.commit()
        
        return ChatResponse(
            success=True,
            response=ai_response,
            message_id=chat_message.message_id
        )
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )

# ===== GET CONVERSATIONS ENDPOINT =====
@router.get("/conversations")
async def get_conversations(
    authorization: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all conversations for the current user
    
    Headers:
        - Authorization: Bearer <token>
    
    Response:
        - success: True/False
        - conversations: List of conversations
    """
    
    try:
        # Authenticate user
        user = get_current_user(authorization, db)
        
        # Get all conversations
        conversations = db.query(Conversation).filter(
            Conversation.user_id == user.user_id
        ).all()
        
        conversations_data = [
            {
                "conversation_id": conv.conversation_id,
                "title": conv.title,
                "doc_id": conv.doc_id,
                "last_time": conv.last_time.isoformat() if conv.last_time else None
            }
            for conv in conversations
        ]
        
        return {
            "success": True,
            "conversations": conversations_data
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve conversations"
        )

# ===== GET CONVERSATION MESSAGES ENDPOINT =====
@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: int,
    authorization: str = None,
    db: Session = Depends(get_db)
):
    """
    Get all messages in a conversation
    
    Path Params:
        - conversation_id: Conversation ID
    
    Headers:
        - Authorization: Bearer <token>
    
    Response:
        - success: True/False
        - messages: List of messages
    """
    
    try:
        # Authenticate user
        user = get_current_user(authorization, db)
        
        # Verify conversation belongs to user
        conversation = db.query(Conversation).filter(
            Conversation.conversation_id == conversation_id,
            Conversation.user_id == user.user_id
        ).first()
        
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )
        
        # Get all messages
        messages = db.query(ChatMessage).filter(
            ChatMessage.conversation_id == conversation_id
        ).all()
        
        messages_data = [
            {
                "message_id": msg.message_id,
                "user_message": msg.user_message,
                "assistant_response": msg.assistant_response,
                "relevant_chunks": msg.relevant_chunks,
                "created_at": msg.created_at.isoformat() if msg.created_at else None
            }
            for msg in messages
        ]
        
        return {
            "success": True,
            "messages": messages_data
        }
    
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve messages"
        )

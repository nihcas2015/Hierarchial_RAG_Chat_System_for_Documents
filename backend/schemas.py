from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# ===== User Schemas =====
class UserBase(BaseModel):
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")

class UserResponse(UserBase):
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True

# ===== Login/Auth Schemas =====
class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str
    token: Optional[str] = None
    userId: Optional[int] = None
    email: Optional[str] = None

class SignupRequest(BaseModel):
    fullname: str = Field(..., min_length=2)
    email: EmailStr
    password: str = Field(..., min_length=8)

class SignupResponse(BaseModel):
    success: bool
    message: str
    userId: Optional[int] = None

# ===== Document Schemas =====
class DocumentBase(BaseModel):
    file_name: str
    content_type: str

class DocumentCreate(DocumentBase):
    file_path: str

class DocumentResponse(DocumentBase):
    doc_id: int
    user_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True

# ===== Document Section Schemas =====
class DocumentSectionBase(BaseModel):
    section_number: int
    section_title: str

class DocumentSectionResponse(DocumentSectionBase):
    section_id: int
    doc_id: int

    class Config:
        from_attributes = True

# ===== Document Chunk Schemas =====
class DocumentChunkBase(BaseModel):
    chunk_text: str
    chunk_number: int

class DocumentChunkResponse(DocumentChunkBase):
    chunk_id: int
    doc_id: int
    section_id: Optional[int] = None

    class Config:
        from_attributes = True

# ===== Conversation Schemas =====
class ConversationBase(BaseModel):
    title: Optional[str] = None
    doc_id: Optional[int] = None

class ConversationCreate(ConversationBase):
    pass

class ConversationResponse(ConversationBase):
    conversation_id: int
    user_id: int
    last_time: datetime

    class Config:
        from_attributes = True

# ===== Chat Message Schemas =====
class ChatMessageBase(BaseModel):
    user_message: str
    assistant_response: Optional[str] = None
    relevant_chunks: Optional[str] = None

class ChatMessageCreate(BaseModel):
    message: str = Field(..., min_length=1)

class ChatMessageResponse(ChatMessageBase):
    message_id: int
    conversation_id: int
    created_at: datetime

    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    success: bool
    response: str
    message_id: Optional[int] = None

# ===== File Upload Schemas =====
class FileUploadResponse(BaseModel):
    success: bool
    message: str
    doc_id: Optional[int] = None
    file_name: Optional[str] = None

# ===== Password Reset Schemas =====
class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ForgotPasswordResponse(BaseModel):
    success: bool
    message: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)

class ResetPasswordResponse(BaseModel):
    success: bool
    message: str

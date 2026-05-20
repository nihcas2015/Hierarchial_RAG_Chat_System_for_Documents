from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from database import Base

# Users Table
class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    documents = relationship("Document", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")

    def __repr__(self):
        return f"<User {self.email}>"


# Documents Table
class Document(Base):
    __tablename__ = "documents"

    doc_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(500))
    content_type = Column(String(50))
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="documents")
    sections = relationship("DocumentSection", back_populates="document")
    chunks = relationship("DocumentChunk", back_populates="document")
    conversations = relationship("Conversation", back_populates="document")

    def __repr__(self):
        return f"<Document {self.file_name}>"


# Document Sections Table
class DocumentSection(Base):
    __tablename__ = "document_sections"

    section_id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False, index=True)
    section_number = Column(Integer)
    section_title = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="sections")
    chunks = relationship("DocumentChunk", back_populates="section")

    def __repr__(self):
        return f"<DocumentSection {self.section_title}>"


# Document Chunks Table
class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    chunk_id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(Integer, ForeignKey("documents.doc_id", ondelete="CASCADE"), nullable=False, index=True)
    section_id = Column(Integer, ForeignKey("document_sections.section_id", ondelete="SET NULL"), index=True)
    chunk_number = Column(Integer)
    chunk_text = Column(Text, nullable=False)
    
    # Contextual RAG fields
    summary = Column(Text, nullable=True)  # Summary of chunk (from Ollama)
    topic = Column(String(255), nullable=True)  # Topic extracted from chunk
    
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)  # When contextual processing completed

    # Relationships
    document = relationship("Document", back_populates="chunks")
    section = relationship("DocumentSection", back_populates="chunks")
    embedding = relationship("ChunkEmbedding", back_populates="chunk", uselist=False)
    summary_embedding = relationship("ChunkSummaryEmbedding", back_populates="chunk", uselist=False)

    def __repr__(self):
        return f"<DocumentChunk {self.chunk_id}>"


# Embeddings Table
class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    embedding_id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    embedding = Column(LargeBinary, nullable=False)
    embedding_model = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chunk = relationship("DocumentChunk", back_populates="embedding")

    def __repr__(self):
        return f"<ChunkEmbedding {self.chunk_id}>"


# Summary Embeddings Table (for contextual RAG)
class ChunkSummaryEmbedding(Base):
    __tablename__ = "chunk_summary_embeddings"

    summary_embedding_id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(Integer, ForeignKey("document_chunks.chunk_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    summary_embedding = Column(LargeBinary, nullable=False)  # Embedding of the summary
    embedding_model = Column(String(100), default="text-embedding-3-small")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    chunk = relationship("DocumentChunk", back_populates="summary_embedding")

    def __repr__(self):
        return f"<ChunkSummaryEmbedding {self.chunk_id}>"


# Conversations Table
class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    doc_id = Column(Integer, ForeignKey("documents.doc_id", ondelete="CASCADE"), index=True)
    title = Column(String(255))
    last_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="conversations")
    document = relationship("Document", back_populates="conversations")
    messages = relationship("ChatMessage", back_populates="conversation")

    def __repr__(self):
        return f"<Conversation {self.title}>"


# Chat Messages Table
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    message_id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)
    user_message = Column(Text)
    assistant_response = Column(Text)
    relevant_chunks = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage {self.message_id}>"

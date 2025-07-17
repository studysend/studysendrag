from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pgvector.sqlalchemy import Vector

Base = declarative_base()

# Database Models
class ChatSession(Base):
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_email = Column(String, nullable=False, index=True)
    course_id = Column(Integer, nullable=False, index=True)
    session_name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    messages = relationship("ChatMessage", back_populates="session")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    message_type = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    message_metadata = Column(JSON, nullable=True)  # Store sources, tokens, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("ChatSession", back_populates="messages")

class DocumentIndex(Base):
    __tablename__ = "document_index"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, nullable=False, index=True)
    doc_name = Column(String, nullable=False)
    doc_url = Column(String, nullable=False)
    s3_key = Column(String, nullable=True)
    parsed_content = Column(Text, nullable=True)
    embedding_status = Column(String, default="pending")  # pending, processing, completed, failed
    processed_at = Column(DateTime, nullable=True)
    chunk_count = Column(Integer, default=0)

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, nullable=False, index=True)
    course_id = Column(Integer, nullable=False, index=True)
    doc_name = Column(String, nullable=False)
    post_name = Column(String, nullable=True)
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    total_chunks = Column(Integer, nullable=False)
    embedding = Column(Vector(1536))  # 1536 dimensions for text-embedding-3-small
    created_at = Column(DateTime, default=datetime.utcnow)

class CourseIndexStatus(Base):
    __tablename__ = "course_index_status"
    
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, nullable=False, unique=True, index=True)
    last_indexed = Column(DateTime, nullable=True)
    document_count = Column(Integer, default=0)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# Pydantic Models for API
class ChatSessionCreate(BaseModel):
    user_email: str
    course_id: int
    session_name: str

class ChatSessionResponse(BaseModel):
    id: int
    user_email: str
    course_id: int
    session_name: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    
    class Config:
        from_attributes = True

class ChatMessageCreate(BaseModel):
    session_id: int
    content: str

class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    message_type: str
    content: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime
    
    class Config:
        from_attributes = True

class ChatResponse(BaseModel):
    message: str
    sources: List[Dict[str, Any]] = []
    session_id: int
    message_id: int

class CourseInfo(BaseModel):
    id: int
    grade: str
    category: str
    subject: str
    document_count: Optional[int] = None

class CourseIndexStatusResponse(BaseModel):
    course_id: int
    status: str
    document_count: int
    chunk_count: int
    last_indexed: Optional[datetime] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class UnindexedCoursesResponse(BaseModel):
    unindexed_courses: List[CourseInfo]
    total_courses: int
    indexed_courses: int
    pending_courses: int
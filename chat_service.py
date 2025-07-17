import os
from openai import OpenAI
from typing import List, Dict, Any, Optional
from vector_store import VectorStore
from database import get_db, get_course_documents
from models import ChatSession, ChatMessage, ChatMessageResponse
from sqlalchemy.orm import Session
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class ChatService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        self.vector_store = VectorStore()
        self.model = "gpt-4o-mini"
        
    def create_chat_session(self, user_email: str, course_id: int, session_name: str, db: Session) -> ChatSession:
        """Create a new chat session"""
        session = ChatSession(
            user_email=user_email,
            course_id=course_id,
            session_name=session_name
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session
    
    def get_user_sessions(self, user_email: str, db: Session) -> List[ChatSession]:
        """Get all active sessions for a user"""
        return db.query(ChatSession).filter(
            ChatSession.user_email == user_email,
            ChatSession.is_active == True
        ).order_by(ChatSession.updated_at.desc()).all()
    
    def get_session_messages(self, session_id: int, db: Session) -> List[ChatMessage]:
        """Get all messages for a session"""
        return db.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).order_by(ChatMessage.timestamp.asc()).all()
    
    def save_message(self, session_id: int, message_type: str, content: str, 
                    metadata: Optional[Dict] = None, db: Session = None) -> ChatMessage:
        """Save a message to the database"""
        message = ChatMessage(
            session_id=session_id,
            message_type=message_type,
            content=content,
            message_metadata=metadata or {}
        )
        db.add(message)
        db.commit()
        db.refresh(message)
        return message
    
    def get_relevant_context(self, query: str, course_id: int, max_chunks: int = 3) -> List[Dict[str, Any]]:
        """Get relevant document chunks for the query"""
        return self.vector_store.search_similar_chunks(
            query=query,
            course_id=course_id,
            n_results=max_chunks
        )
    
    def build_system_prompt(self, course_id: int, course_info: Dict[str, Any]) -> str:
        """Build system prompt with course context"""
        return f"""You are an AI tutor specializing in {course_info.get('subject', 'the subject')} 
for {course_info.get('grade', 'students')}. You help students understand course materials, 
answer questions, and provide explanations based on the provided course documents.

Course Context:
- Subject: {course_info.get('subject', 'N/A')}
- Grade Level: {course_info.get('grade', 'N/A')}
- Category: {course_info.get('category', 'N/A')}

Guidelines:
1. Use the provided document context to answer questions accurately
2. If information isn't in the documents, clearly state that
3. Provide clear, educational explanations appropriate for the grade level
4. Encourage learning and critical thinking
5. Be helpful, patient, and supportive
6. Cite sources when referencing specific document content"""
    
    def generate_response(self, query: str, session_id: int, course_id: int, 
                         course_info: Dict[str, Any], chat_history: List[Dict[str, str]], 
                         db: Session) -> Dict[str, Any]:
        """Generate AI response with RAG context"""
        try:
            # Get relevant document chunks
            relevant_chunks = self.get_relevant_context(query, course_id)
            
            # Build context from relevant chunks
            context_text = ""
            sources = []
            
            if relevant_chunks:
                context_text = "\n\nRelevant Course Material:\n"
                for i, chunk in enumerate(relevant_chunks, 1):
                    context_text += f"\n[Source {i}]: {chunk['content']}\n"
                    sources.append({
                        "source_id": i,
                        "doc_name": chunk['metadata'].get('doc_name', 'Unknown'),
                        "post_name": chunk['metadata'].get('post_name', 'Unknown'),
                        "similarity_score": chunk['similarity_score']
                    })
            
            # Build messages for OpenAI
            messages = [
                {"role": "system", "content": self.build_system_prompt(course_id, course_info)}
            ]
            
            # Add chat history (last 10 messages to stay within token limits)
            for msg in chat_history[-10:]:
                messages.append(msg)
            
            # Add current query with context
            user_message = f"{query}{context_text}"
            messages.append({"role": "user", "content": user_message})
            
            # Generate response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            # Save user message
            user_msg = self.save_message(
                session_id=session_id,
                message_type="user",
                content=query,
                db=db
            )
            
            # Save AI response
            ai_msg = self.save_message(
                session_id=session_id,
                message_type="assistant",
                content=ai_response,
                metadata={"sources": sources, "tokens_used": response.usage.total_tokens},
                db=db
            )
            
            return {
                "message": ai_response,
                "sources": sources,
                "session_id": session_id,
                "message_id": ai_msg.id,
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            logger.error(f"Failed to generate response: {str(e)}")
            
            # Save user message even if AI response fails
            self.save_message(
                session_id=session_id,
                message_type="user",
                content=query,
                db=db
            )
            
            # Save error response
            error_msg = self.save_message(
                session_id=session_id,
                message_type="assistant",
                content="I apologize, but I'm having trouble generating a response right now. Please try again.",
                metadata={"error": str(e)},
                db=db
            )
            
            return {
                "message": "I apologize, but I'm having trouble generating a response right now. Please try again.",
                "sources": [],
                "session_id": session_id,
                "message_id": error_msg.id,
                "error": str(e)
            }
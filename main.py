from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import (
    get_db, create_tables, get_existing_courses, get_course_documents,
    get_unindexed_courses, get_course_index_status, update_course_index_status
)
from models import (
    ChatSessionCreate, ChatSessionResponse, ChatMessageCreate, 
    ChatMessageResponse, ChatResponse, CourseInfo, CourseIndexStatusResponse,
    UnindexedCoursesResponse, ChatSession
)
from chat_service import ChatService
from document_processor import DocumentProcessor
from vector_store import VectorStore
from redis_service import redis_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="RAG Study Chat API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
chat_service = ChatService()
doc_processor = DocumentProcessor()
vector_store = VectorStore()

# Initialize scheduler for periodic tasks
scheduler = AsyncIOScheduler()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Database tables created/verified")
    
    # Start periodic course indexing check (every 5 minutes)
    scheduler.add_job(
        check_and_index_new_courses,
        trigger=IntervalTrigger(minutes=5),
        id='course_indexing_check',
        name='Check and index new courses',
        replace_existing=True
    )
    scheduler.start()
    logger.info("Started periodic course indexing scheduler")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("Scheduler shut down")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "RAG Study Chat API is running"}

# Get all available courses
@app.get("/courses", response_model=List[CourseInfo])
async def get_courses():
    """Get all available courses"""
    try:
        courses = get_existing_courses()
        return courses
    except Exception as e:
        logger.error(f"Failed to get courses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve courses")

# Get documents for a specific course
@app.get("/courses/{course_id}/documents")
async def get_course_docs(course_id: int):
    """Get all documents for a specific course"""
    try:
        documents = get_course_documents(course_id)
        doc_count = vector_store.get_course_document_count(course_id)
        
        return {
            "course_id": course_id,
            "documents": documents,
            "indexed_chunks": doc_count
        }
    except Exception as e:
        logger.error(f"Failed to get course documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve course documents")

# Get unindexed courses - Frontend can call this to check what needs indexing
@app.get("/courses/unindexed", response_model=UnindexedCoursesResponse)
async def get_unindexed_courses_endpoint():
    """Get courses that haven't been indexed yet"""
    try:
        unindexed = get_unindexed_courses()
        all_courses = get_existing_courses()
        
        # Count courses with documents
        courses_with_docs = len([c for c in all_courses if any(doc['course_id'] == c['id'] for doc in get_course_documents(c['id']))])
        indexed_count = courses_with_docs - len(unindexed)
        
        return UnindexedCoursesResponse(
            unindexed_courses=unindexed,
            total_courses=courses_with_docs,
            indexed_courses=indexed_count,
            pending_courses=len(unindexed)
        )
    except Exception as e:
        logger.error(f"Failed to get unindexed courses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve unindexed courses")

# Get course index status
@app.get("/courses/{course_id}/index-status", response_model=CourseIndexStatusResponse)
async def get_course_index_status_endpoint(course_id: int):
    """Get indexing status for a specific course"""
    try:
        status = get_course_index_status(course_id)
        if not status:
            # Course not indexed yet
            return CourseIndexStatusResponse(
                course_id=course_id,
                status="not_indexed",
                document_count=0,
                chunk_count=0
            )
        
        return CourseIndexStatusResponse(
            course_id=status.course_id,
            status=status.status,
            document_count=status.document_count,
            chunk_count=status.chunk_count,
            last_indexed=status.last_indexed,
            error_message=status.error_message
        )
    except Exception as e:
        logger.error(f"Failed to get course index status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve course index status")

# Trigger indexing for unindexed courses
@app.post("/courses/index-unindexed")
async def index_unindexed_courses(background_tasks: BackgroundTasks):
    """Index all unindexed courses"""
    try:
        unindexed = get_unindexed_courses()
        
        if not unindexed:
            return {"message": "No courses need indexing", "courses_to_index": 0}
        
        # Add background task to index all unindexed courses
        background_tasks.add_task(index_multiple_courses_task, [course['id'] for course in unindexed])
        
        return {
            "message": f"Started indexing {len(unindexed)} courses",
            "courses_to_index": len(unindexed),
            "courses": [{"id": c['id'], "subject": c['subject']} for c in unindexed]
        }
    except Exception as e:
        logger.error(f"Failed to start indexing unindexed courses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start indexing process")

# Process documents for a course (background task)
@app.post("/courses/{course_id}/process-documents")
async def process_course_documents(course_id: int, background_tasks: BackgroundTasks):
    """Process and index all documents for a course"""
    try:
        documents = get_course_documents(course_id)
        
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found for this course")
        
        # Add background task to process documents
        background_tasks.add_task(process_documents_task, course_id, documents)
        
        return {
            "message": f"Started processing {len(documents)} documents for course {course_id}",
            "course_id": course_id,
            "document_count": len(documents)
        }
    except Exception as e:
        logger.error(f"Failed to start document processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to start document processing")

async def process_documents_task(course_id: int, documents: List[dict]):
    """Background task to process documents"""
    logger.info(f"Starting document processing for course {course_id}")
    
    for doc in documents:
        try:
            # Process document
            result = doc_processor.process_document(doc['doc_url'], doc['doc_name'])
            
            if result['success']:
                # Chunk the content
                chunks = doc_processor.chunk_text(result['parsed_content'])
                
                # Prepare metadata for each chunk
                metadata_list = []
                for i, chunk in enumerate(chunks):
                    metadata_list.append({
                        "post_id": doc['post_id'],
                        "course_id": course_id,
                        "doc_name": doc['doc_name'],
                        "post_name": doc['post_name'],
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    })
                
                # Add to vector store
                vector_store.add_document_chunks(chunks, metadata_list)
                logger.info(f"Processed document: {doc['doc_name']} ({len(chunks)} chunks)")
                
                # Invalidate course cache since new content was added
                redis_service.invalidate_course_cache(course_id)
            else:
                logger.error(f"Failed to process document {doc['doc_name']}: {result['error']}")
                
        except Exception as e:
            logger.error(f"Error processing document {doc['doc_name']}: {str(e)}")
    
    logger.info(f"Completed document processing for course {course_id}")

async def index_multiple_courses_task(course_ids: List[int]):
    """Background task to index multiple courses"""
    logger.info(f"Starting indexing for {len(course_ids)} courses")
    
    for course_id in course_ids:
        try:
            # Update status to processing
            update_course_index_status(course_id, "processing")
            
            # Get documents for this course
            documents = get_course_documents(course_id)
            
            if not documents:
                update_course_index_status(course_id, "completed", 0, 0)
                continue
            
            total_chunks = 0
            successful_docs = 0
            
            for doc in documents:
                try:
                    # Process document
                    result = doc_processor.process_document(doc['doc_url'], doc['doc_name'])
                    
                    if result['success']:
                        # Chunk the content
                        chunks = doc_processor.chunk_text(result['parsed_content'])
                        
                        # Prepare metadata for each chunk
                        metadata_list = []
                        for i, chunk in enumerate(chunks):
                            metadata_list.append({
                                "post_id": doc['post_id'],
                                "course_id": course_id,
                                "doc_name": doc['doc_name'],
                                "post_name": doc['post_name'],
                                "chunk_index": i,
                                "total_chunks": len(chunks)
                            })
                        
                        # Add to vector store
                        if vector_store.add_document_chunks(chunks, metadata_list):
                            total_chunks += len(chunks)
                            successful_docs += 1
                            logger.info(f"Indexed document: {doc['doc_name']} ({len(chunks)} chunks)")
                        else:
                            logger.error(f"Failed to add chunks for document {doc['doc_name']}")
                    else:
                        logger.error(f"Failed to process document {doc['doc_name']}: {result['error']}")
                        
                except Exception as e:
                    logger.error(f"Error processing document {doc['doc_name']}: {str(e)}")
            
            # Update final status
            if successful_docs > 0:
                update_course_index_status(course_id, "completed", successful_docs, total_chunks)
                logger.info(f"Successfully indexed course {course_id}: {successful_docs} docs, {total_chunks} chunks")
            else:
                update_course_index_status(course_id, "failed", 0, 0, "No documents could be processed")
                logger.error(f"Failed to index any documents for course {course_id}")
                
        except Exception as e:
            logger.error(f"Error indexing course {course_id}: {str(e)}")
            update_course_index_status(course_id, "failed", 0, 0, str(e))
    
    logger.info(f"Completed indexing for {len(course_ids)} courses")

async def check_and_index_new_courses():
    """Periodic task to check for new courses and index them"""
    try:
        logger.info("Checking for new courses to index...")
        unindexed = get_unindexed_courses()
        
        if unindexed:
            logger.info(f"Found {len(unindexed)} unindexed courses, starting indexing...")
            await index_multiple_courses_task([course['id'] for course in unindexed])
        else:
            logger.info("No new courses to index")
            
    except Exception as e:
        logger.error(f"Error in periodic course indexing check: {str(e)}")

# Create a new chat session
@app.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_session(session_data: ChatSessionCreate, db: Session = Depends(get_db)):
    """Create a new chat session"""
    try:
        session = chat_service.create_chat_session(
            user_email=session_data.user_email,
            course_id=session_data.course_id,
            session_name=session_data.session_name,
            db=db
        )
        return session
    except Exception as e:
        logger.error(f"Failed to create chat session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create chat session")

# Get user's chat sessions
@app.get("/chat/sessions/{user_email}", response_model=List[ChatSessionResponse])
async def get_user_sessions(user_email: str, db: Session = Depends(get_db)):
    """Get all active sessions for a user"""
    try:
        sessions = chat_service.get_user_sessions(user_email, db)
        return sessions
    except Exception as e:
        logger.error(f"Failed to get user sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve user sessions")

# Get session messages
@app.get("/chat/sessions/{session_id}/messages", response_model=List[ChatMessageResponse])
async def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    """Get all messages for a session"""
    try:
        messages = chat_service.get_session_messages(session_id, db)
        return messages
    except Exception as e:
        logger.error(f"Failed to get session messages: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve session messages")

# Send a chat message
@app.post("/chat/message", response_model=ChatResponse)
async def send_message(message_data: ChatMessageCreate, db: Session = Depends(get_db)):
    """Send a message and get AI response"""
    try:
        # Get session info
        session = db.query(ChatSession).filter(
            ChatSession.id == message_data.session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Get course info
        courses = get_existing_courses()
        course_info = next((c for c in courses if c['id'] == session.course_id), {})
        
        # Get chat history
        messages = chat_service.get_session_messages(message_data.session_id, db)
        chat_history = []
        for msg in messages[-10:]:  # Last 10 messages
            chat_history.append({
                "role": "user" if msg.message_type == "user" else "assistant",
                "content": msg.content
            })
        
        # Generate response
        response = chat_service.generate_response(
            query=message_data.content,
            session_id=message_data.session_id,
            course_id=session.course_id,
            course_info=course_info,
            chat_history=chat_history,
            db=db
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process message")

# Delete a chat session
@app.delete("/chat/sessions/{session_id}")
async def delete_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a chat session"""
    try:
        session = db.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session.is_active = False
        db.commit()
        
        return {"message": "Session deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete session")

# Redis Cache Management Endpoints

@app.get("/cache/stats")
async def get_cache_stats():
    """Get Redis cache statistics"""
    try:
        stats = redis_service.get_cache_stats()
        return {
            "cache_stats": stats,
            "timestamp": "2025-01-17T10:30:00Z"
        }
    except Exception as e:
        logger.error(f"Failed to get cache stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve cache statistics")

@app.post("/cache/invalidate/course/{course_id}")
async def invalidate_course_cache(course_id: int):
    """Invalidate all cache entries for a specific course"""
    try:
        deleted_count = redis_service.invalidate_course_cache(course_id)
        
        # Also invalidate general course list cache
        redis_service.delete("all_courses")
        
        return {
            "message": f"Invalidated cache for course {course_id}",
            "deleted_entries": deleted_count,
            "course_id": course_id
        }
    except Exception as e:
        logger.error(f"Failed to invalidate course cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to invalidate course cache")

@app.post("/cache/invalidate/all")
async def invalidate_all_cache():
    """Invalidate all cache entries (use with caution)"""
    try:
        if not redis_service.enabled:
            return {"message": "Redis caching is disabled", "deleted_entries": 0}
        
        # Get all keys and delete them
        deleted_count = redis_service.delete_pattern("*")
        
        return {
            "message": "Invalidated all cache entries",
            "deleted_entries": deleted_count
        }
    except Exception as e:
        logger.error(f"Failed to invalidate all cache: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to invalidate all cache")

@app.get("/cache/health")
async def cache_health_check():
    """Check Redis cache health"""
    try:
        if not redis_service.enabled:
            return {
                "status": "disabled",
                "message": "Redis caching is disabled"
            }
        
        # Test basic operations
        test_key = "health_check_test"
        test_value = "test_value"
        
        # Test SET
        set_success = redis_service.set(test_key, test_value, ttl=10)
        
        # Test GET
        get_value = redis_service.get(test_key)
        
        # Test DELETE
        delete_success = redis_service.delete(test_key)
        
        if set_success and get_value == test_value and delete_success:
            return {
                "status": "healthy",
                "message": "Redis cache is working properly",
                "operations_tested": ["set", "get", "delete"]
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Redis cache operations failed",
                "set_success": set_success,
                "get_success": get_value == test_value,
                "delete_success": delete_success
            }
            
    except Exception as e:
        logger.error(f"Cache health check failed: {str(e)}")
        return {
            "status": "error",
            "message": f"Cache health check failed: {str(e)}"
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
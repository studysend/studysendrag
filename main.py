from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, File, UploadFile, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
import logging
import asyncio
import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from database import (
    get_db, create_tables, get_existing_courses, get_course_documents,
    get_unindexed_courses, get_course_index_status, update_course_index_status,
    SessionLocal
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
from background_processor import BackgroundProcessor, ProcessStatus

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="RAG Study Chat API", version="1.0.0")

# Add validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error for {request.url}: {exc.errors()}")
    logger.error(f"Request body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

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
background_processor = BackgroundProcessor()

# Initialize scheduler for periodic tasks
scheduler = AsyncIOScheduler()

# Create tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()
    logger.info("Database tables created/verified")
    
    # Start background processor
    await background_processor.start()
    logger.info("Background processor started")
    
    # Disable automatic background indexing to prevent API blocking
    # scheduler.add_job(
    #     check_and_index_new_courses,
    #     trigger=IntervalTrigger(minutes=30),  # Reduced frequency
    #     id='course_indexing_check',
    #     name='Check and index new courses',
    #     replace_existing=True
    # )
    # scheduler.start()
    logger.info("Background indexing disabled for better API performance")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    await background_processor.stop()
    logger.info("Services shut down")

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "RAG Study Chat API is running"}

# Get courses with documents
@app.get("/courses", response_model=List[CourseInfo])
async def get_courses():
    """Get all courses that have documents"""
    try:
        courses = get_existing_courses()
        return courses
    except Exception as e:
        logger.error(f"Failed to get courses: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve courses")

# Get posts/documents for a specific course
@app.get("/courses/{course_id}/posts")
async def get_course_posts(course_id: int, db: Session = Depends(get_db)):
    """Get all posts/documents for a specific course"""
    try:
        result = db.execute(text("""
            SELECT p.id, p.post_name
            FROM post p 
            WHERE p.course_id = :course_id 
            ORDER BY p.post_name
        """), {"course_id": course_id})
        
        posts = []
        for row in result.fetchall():
            posts.append({
                "id": row[0],
                "post_name": row[1]
            })
        
        return {"course_id": course_id, "posts": posts, "total": len(posts)}
    except Exception as e:
        logger.error(f"Failed to get posts for course {course_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve posts: {str(e)}")

# Get all available posts across all courses
@app.get("/posts")
async def get_all_posts(db: Session = Depends(get_db)):
    """Get all posts/documents that can be used for chat sessions"""
    try:
        # Query without url filter since it doesn't exist
        result = db.execute(text("""
            SELECT p.id, p.post_name, p.course_id, c.subject, c.grade, c.category
            FROM post p 
            JOIN courses c ON p.course_id = c.id
            ORDER BY c.subject, p.post_name
        """))
        
        posts = []
        for row in result.fetchall():
            posts.append({
                "id": row[0],
                "post_name": row[1],
                "course_id": row[2],
                "subject": row[3],
                "grade": row[4],
                "category": row[5]
            })
        
        return {"posts": posts, "total": len(posts)}
    except Exception as e:
        logger.error(f"Failed to get all posts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve posts: {str(e)}")

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

# Post-based indexing endpoints
@app.post("/posts/{post_id}/process-document")
async def process_post_document(
    post_id: int,
    course_id: int,
    file: UploadFile = File(...)
):
    """Process a document for a specific post and add to vector store"""
    try:
        # Save uploaded file temporarily
        import tempfile
        import os
        
        suffix = os.path.splitext(file.filename)[1] if file.filename else '.txt'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process the document
            document_processor = DocumentProcessor()
            processing_result = document_processor.process_document(temp_file_path, file.filename or "unnamed")
            
            if not processing_result['success']:
                raise Exception(f"Failed to process document: {processing_result['error']}")
            
            # Chunk the content
            chunks = document_processor.chunk_text(processing_result['parsed_content'])
            
            # Prepare metadata for each chunk
            metadata_list = []
            for i, chunk in enumerate(chunks):
                metadata_list.append({
                    "post_id": post_id,
                    "course_id": course_id,
                    "doc_name": file.filename or "unnamed",
                    "post_name": f"Post {post_id}",
                    "chunk_index": i,
                    "source": f"Post {post_id} - {file.filename or 'unnamed'}"
                })
            
            # Store in vector store
            vector_store = VectorStore()
            success = vector_store.add_document_chunks(chunks, metadata_list)
            
            if not success:
                raise Exception("Failed to store document chunks in vector store")
            
            # Invalidate cache
            redis_service.delete(f"post_search:{post_id}")
            
            return {
                "message": "Document processed successfully",
                "chunks_count": len(chunks),
                "post_id": post_id,
                "document_name": file.filename
            }
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
            
    except Exception as e:
        logger.error(f"Error processing document for post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/posts/{post_id}/process-document-async")
async def process_post_document_async(
    post_id: int,
    course_id: int,
    file: UploadFile = File(...)
):
    """Asynchronously process a document for a specific post"""
    try:
        # Save uploaded file temporarily
        import tempfile
        import os
        
        suffix = os.path.splitext(file.filename)[1] if file.filename else '.txt'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Submit to background processor
        process_id = background_processor.submit_file_processing(
            post_id=post_id,
            course_id=course_id,
            file_path=temp_file_path,
            doc_name=file.filename or "unnamed",
            post_name=f"Post {post_id}"
        )
        
        return {
            "process_id": process_id,
            "message": "Document processing started",
            "post_id": post_id,
            "document_name": file.filename,
            "status_url": f"/process/{process_id}/status"
        }
            
    except Exception as e:
        logger.error(f"Error starting document processing for post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/process/{process_id}/status")
async def get_process_status(process_id: str):
    """Get the status of a background process"""
    try:
        process_info = background_processor.get_process_status(process_id)
        if not process_info:
            raise HTTPException(status_code=404, detail="Process not found")
        
        return {
            "process_id": process_id,
            "status": process_info.status.value,
            "progress": process_info.progress,
            "message": process_info.message,
            "created_at": process_info.created_at.isoformat(),
            "started_at": process_info.started_at.isoformat() if process_info.started_at else None,
            "completed_at": process_info.completed_at.isoformat() if process_info.completed_at else None,
            "error": process_info.error_message
        }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting process status {process_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/posts/{post_id}/index-status")
async def get_post_index_status(post_id: int, db: Session = Depends(get_db)):
    """Get indexing status for a specific post"""
    try:
        logger.info(f"Getting index status for post {post_id}")
        
        # Get post information
        result = db.execute(text("""
            SELECT p.id, p.post_name, p.doc_url, p.doc_name, c.id as course_id, c.subject
            FROM post p 
            JOIN courses c ON p.course_id = c.id 
            WHERE p.id = :post_id
        """), {"post_id": post_id})
        
        post_row = result.fetchone()
        if not post_row:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")
        
        post_info = {
            "post_id": post_row[0],
            "post_name": post_row[1],
            "doc_url": post_row[2],
            "doc_name": post_row[3],
            "course_id": post_row[4],
            "subject": post_row[5]
        }
        
        # Check if document exists in vector store
        chunks_count = 0
        is_indexed = False
        
        if post_info["doc_url"] and post_info["doc_name"]:
            # Get chunk count directly from database
            try:
                chunks_count = vector_store.get_post_document_count(post_id)
                is_indexed = chunks_count > 0
                logger.info(f"Found {chunks_count} chunks for post {post_id}")
            except Exception as e:
                logger.warning(f"Error checking vector store for post {post_id}: {str(e)}")
        
        status = "indexed" if is_indexed else "not_indexed"
        if not post_info["doc_url"] or not post_info["doc_name"]:
            status = "no_document"
        
        return {
            "post_id": post_id,
            "post_name": post_info["post_name"],
            "doc_name": post_info["doc_name"],
            "doc_url": post_info["doc_url"],
            "course_id": post_info["course_id"],
            "subject": post_info["subject"],
            "status": status,
            "chunks_count": chunks_count,
            "is_indexed": is_indexed,
            "has_document": bool(post_info["doc_url"] and post_info["doc_name"])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting index status for post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting index status: {str(e)}")

# Create a new chat session
@app.post("/chat/sessions", response_model=ChatSessionResponse)
async def create_session(session_data: ChatSessionCreate, db: Session = Depends(get_db)):
    """Create a new chat session for a specific post"""
    try:
        logger.info(f"Creating session for user {session_data.user_email}, post {session_data.post_id}")
        
        # Validate post exists if post_id is provided
        if session_data.post_id:
            result = db.execute(text("""
                SELECT p.id, p.post_name, c.subject 
                FROM post p 
                JOIN courses c ON p.course_id = c.id 
                WHERE p.id = :post_id
            """), {"post_id": session_data.post_id})
            post_row = result.fetchone()
            
            if not post_row:
                logger.warning(f"Post {session_data.post_id} not found")
                raise HTTPException(status_code=404, detail=f"Post {session_data.post_id} not found")
            
            logger.info(f"Validated post {session_data.post_id}: {post_row[1]}")
        
        session = chat_service.create_chat_session(
            user_email=session_data.user_email,
            post_id=session_data.post_id,
            session_name=session_data.session_name,
            db=db
        )
        
        logger.info(f"Successfully created session {session.id}")
        return session
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create chat session: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create chat session: {str(e)}")

# Get user's chat sessions
@app.get("/chat/sessions/{user_email}", response_model=List[ChatSessionResponse])
async def get_user_sessions(user_email: str, db: Session = Depends(get_db)):
    """Get all active sessions for a user"""
    try:
        logger.info(f"Getting sessions for user: {user_email}")
        sessions = chat_service.get_user_sessions(user_email, db)
        logger.info(f"Found {len(sessions)} sessions for user {user_email}")
        return sessions
    except Exception as e:
        logger.error(f"Failed to get user sessions for {user_email}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve user sessions: {str(e)}")

# Get session messages
@app.get("/chat/sessions/{session_id}/messages")
async def get_session_messages(session_id: int, db: Session = Depends(get_db)):
    """Get all messages for a session"""
    try:
        logger.info(f"Retrieving messages for session {session_id}")
        
        # Check if session exists
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            logger.warning(f"Session {session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
            
        logger.info(f"Session {session_id} found - getting messages")
        
        # Use raw SQL to avoid SQLAlchemy object complications
        result = db.execute(text("""
            SELECT id, session_id, message_type, content, message_metadata, timestamp 
            FROM chat_messages 
            WHERE session_id = :session_id 
            ORDER BY timestamp ASC
        """), {"session_id": session_id})
        
        messages_data = result.fetchall()
        logger.info(f"Found {len(messages_data)} messages for session {session_id}")
        
        # Convert to simple dictionaries using raw data with explicit type checking
        response_messages = []
        for i, row in enumerate(messages_data):
            try:
                # Row indices: 0=id, 1=session_id, 2=message_type, 3=content, 4=message_metadata, 5=timestamp
                raw_metadata = row[4]  # message_metadata column
                
                logger.info(f"Processing row {i}: metadata type = {type(raw_metadata)}, value = {repr(raw_metadata)}")
                
                # Very strict metadata handling - ensure it's always a plain dict
                if raw_metadata is None:
                    clean_metadata = {}
                elif isinstance(raw_metadata, dict):
                    # Create a completely new dict to avoid any SQLAlchemy references
                    clean_metadata = {}
                    for k, v in raw_metadata.items():
                        if isinstance(k, str) and not str(k).startswith('_'):
                            clean_metadata[str(k)] = v
                else:
                    clean_metadata = {}
                
                logger.info(f"Clean metadata for row {i}: type = {type(clean_metadata)}, value = {repr(clean_metadata)}")
                
                # Create response with completely clean data types
                response_msg = {
                    "id": int(row[0]),
                    "session_id": int(row[1]),
                    "message_type": str(row[2]),
                    "content": str(row[3]),
                    "metadata": clean_metadata,  # Guaranteed to be a clean dict
                    "timestamp": str(row[5]) if row[5] else ""
                }
                logger.info(f"Response message {i}: {type(response_msg)}")
                response_messages.append(response_msg)
                logger.info(f"Processed message {row[0]} successfully")
                
            except Exception as msg_error:
                logger.error(f"Error processing message row: {msg_error}")
                # Add a basic message without metadata if processing fails
                try:
                    response_msg = {
                        "id": int(row[0]),
                        "session_id": int(row[1]),
                        "message_type": str(row[2]),
                        "content": str(row[3]),
                        "metadata": {},
                        "timestamp": str(row[5]) if row[5] else ""
                    }
                    response_messages.append(response_msg)
                except:
                    continue
        
        logger.info(f"Successfully converted {len(response_messages)} messages to response format")
        
        # Return as raw JSON response to completely bypass FastAPI validation
        import json
        return Response(
            content=json.dumps(response_messages),
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session messages for session {session_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve session messages")# Send a chat message
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
        
        # Get post info if session has post_id, otherwise fallback to course info
        if session.post_id:
            # Get post information from database
            result = db.execute(text("""
                SELECT p.id, p.post_name, c.grade, c.category, c.subject 
                FROM post p 
                JOIN courses c ON p.course_id = c.id 
                WHERE p.id = :post_id
            """), {"post_id": session.post_id})
            post_row = result.fetchone()
            
            if post_row:
                post_info = {
                    "post_id": post_row[0],
                    "post_name": post_row[1],
                    "grade": post_row[2],
                    "category": post_row[3],
                    "subject": post_row[4]
                }
            else:
                raise HTTPException(status_code=404, detail="Post not found")
        else:
            # Fallback to course-based approach for backward compatibility
            courses = get_existing_courses()
            course_info = next((c for c in courses if c['id'] == session.course_id), {})
            post_info = {
                "post_id": None,
                "post_name": f"{course_info.get('subject', 'Course')} Materials",
                "grade": course_info.get('grade', 'Unknown'),
                "category": course_info.get('category', 'Unknown'),
                "subject": course_info.get('subject', 'Unknown')
            }
        
        # Get chat history
        messages = chat_service.get_session_messages(message_data.session_id, db)
        chat_history = []
        for msg in messages[-10:]:  # Last 10 messages
            chat_history.append({
                "role": "user" if msg.message_type == "user" else "assistant",
                "content": msg.content
            })
        
        # Generate response using post_id if available, otherwise course_id
        if session.post_id:
            response = chat_service.generate_response(
                query=message_data.content,
                session_id=message_data.session_id,
                post_id=session.post_id,
                post_info=post_info,
                chat_history=chat_history,
                db=db
            )
        else:
            # Fallback to old method for backward compatibility
            response = chat_service.generate_response(
                query=message_data.content,
                session_id=message_data.session_id,
                course_id=session.course_id,
                course_info=post_info,
                chat_history=chat_history,
                db=db
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process message")

# Send a streaming chat message
@app.post("/chat/message/stream")
async def send_streaming_message(message_data: ChatMessageCreate):
    """Send a message and get streaming AI response using Server-Sent Events"""
    logger.info(f"Received streaming message request: session_id={message_data.session_id}, content_length={len(message_data.content)}")
    try:
        # Use a temporary database session to get initial info, then close it
        temp_db = SessionLocal()
        try:
            # Get session info
            session = temp_db.query(ChatSession).filter(
                ChatSession.id == message_data.session_id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Store the needed values from the session
            session_post_id = session.post_id
            session_course_id = session.course_id
            
            # Get post info if session has post_id, otherwise fallback to course info
            post_info = None
            course_info = None
            
            if session_post_id:
                # Get post and course info
                result = temp_db.execute(text("""
                    SELECT p.id, p.post_name, p.doc_name, p.doc_url, c.id as course_id, c.subject, c.grade
                    FROM post p 
                    JOIN courses c ON p.course_id = c.id 
                    WHERE p.id = :post_id
                """), {"post_id": session_post_id})
                post_row = result.fetchone()
                
                if post_row:
                    post_info = {
                        "post_id": post_row[0],
                        "post_name": post_row[1],
                        "doc_name": post_row[2],
                        "doc_url": post_row[3],
                        "course_id": post_row[4],
                        "subject": post_row[5],
                        "grade": post_row[6]
                    }
            else:
                # Fallback to course info for backward compatibility
                result = temp_db.execute(text("""
                    SELECT c.id, c.subject, c.grade
                    FROM courses c 
                    WHERE c.id = :course_id
                """), {"course_id": session_course_id})
                course_row = result.fetchone()
                
                if course_row:
                    course_info = {
                        "course_id": course_row[0],
                        "course_subject": course_row[1],
                        "course_grade": course_row[2]
                    }
            
            # Get chat history
            messages = chat_service.get_session_messages(message_data.session_id, temp_db)
            chat_history = []
            for msg in messages[-10:]:  # Last 10 messages
                chat_history.append({
                    "role": "user" if str(msg.message_type) == "user" else "assistant",
                    "content": str(msg.content)
                })
        finally:
            temp_db.close()
        
        # Create the streaming generator
        def generate_streaming_response():
            try:
                # Generate streaming response using post_id if available, otherwise course_id
                if session_post_id:
                    stream_generator = chat_service.generate_streaming_response(
                        query=message_data.content,
                        session_id=message_data.session_id,
                        post_id=session_post_id,
                        post_info=post_info,
                        chat_history=chat_history,
                        db=None,  # Pass None to force new connections within the generator
                        action_type=message_data.action_type
                    )
                else:
                    stream_generator = chat_service.generate_streaming_response(
                        query=message_data.content,
                        session_id=message_data.session_id,
                        course_id=session_course_id,
                        course_info=course_info,
                        chat_history=chat_history,
                        db=None  # Pass None to force new connections within the generator
                    )
                
                # Stream the response chunks
                for chunk in stream_generator:
                    yield f"data: {json.dumps(chunk)}\n\n"
                
            except Exception as e:
                logger.error(f"Error in streaming response: {str(e)}")
                error_chunk = {
                    "error": f"Error generating response: {str(e)}",
                    "session_id": message_data.session_id,
                    "done": True
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
        
        # Return streaming response
        return StreamingResponse(
            generate_streaming_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to setup streaming message: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to setup streaming response")

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

# Background Processing Endpoints
@app.post("/posts/{post_id}/process-background")
async def process_post_background(post_id: int, db: Session = Depends(get_db)):
    """Start background processing for a post document with progress tracking"""
    try:
        # Get the post document information
        result = db.execute(text("""
            SELECT p.id, p.post_name, p.doc_url, p.doc_name, c.id as course_id
            FROM post p
            JOIN courses c ON p.course_id = c.id
            WHERE p.id = :post_id
        """), {"post_id": post_id})

        post_row = result.fetchone()
        if not post_row:
            raise HTTPException(status_code=404, detail=f"Post {post_id} not found")

        if not post_row[2] or not post_row[3]:  # doc_url or doc_name
            raise HTTPException(status_code=400, detail=f"Post {post_id} has no document to process")

        # Check if document is already indexed to avoid duplicate embeddings
        chunks_count = vector_store.get_post_document_count(post_id)
        if chunks_count > 0:
            logger.info(f"Post {post_id} already has {chunks_count} chunks indexed, skipping re-indexing")
            return {
                "process_id": f"already-indexed-{post_id}",
                "status": "completed",
                "message": f"Document already indexed with {chunks_count} chunks. Using existing embeddings.",
                "post_id": post_id,
                "post_name": post_row[1],
                "chunks_count": chunks_count,
                "already_indexed": True
            }

        # Submit the background task
        process_id = background_processor.submit_document_processing(
            post_id=post_id,
            db=db
        )
        
        # Get the process info
        process_info = background_processor.get_process_status(process_id)
        if not process_info:
            raise HTTPException(status_code=500, detail="Failed to create background process")
        
        return {
            "process_id": process_info.process_id,
            "status": process_info.status.value,
            "message": f"Started background processing for post {post_id}",
            "post_id": post_id,
            "post_name": post_row[1],
            "estimated_time": "2-5 minutes"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start background processing for post {post_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")

@app.get("/background/process/{process_id}")
async def get_background_process_status(process_id: str):
    """Get the status of a background processing task"""
    try:
        process_info = background_processor.get_process_status(process_id)
        
        if not process_info:
            raise HTTPException(status_code=404, detail="Process not found")
        
        response = {
            "process_id": process_info.process_id,
            "status": process_info.status.value,
            "progress": process_info.progress,
            "message": process_info.message,
            "started_at": process_info.started_at.isoformat() if process_info.started_at else None,
            "completed_at": process_info.completed_at.isoformat() if process_info.completed_at else None
        }
        
        if process_info.status == ProcessStatus.COMPLETED:
            response["success"] = True
        elif process_info.status == ProcessStatus.FAILED:
            response["error"] = process_info.error_message
            
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get process status for {process_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get process status: {str(e)}")

@app.get("/background/processes")
async def list_processes():
    """List all background processes"""
    try:
        processes = background_processor.list_processes()
        
        return {
            "processes": [
                {
                    "process_id": p.process_id,
                    "status": p.status.value,
                    "progress": p.progress,
                    "started_at": p.started_at.isoformat() if p.started_at else None,
                    "completed_at": p.completed_at.isoformat() if p.completed_at else None,
                    "message": p.message
                }
                for p in processes.values()
            ],
            "total": len(processes)
        }
        
    except Exception as e:
        logger.error(f"Failed to list processes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list processes: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8100)
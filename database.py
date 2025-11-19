import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from models import Base, CourseIndexStatus
from dotenv import load_dotenv
import logging
from datetime import datetime
from redis_service import redis_service

load_dotenv()
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def create_tables():
    """Create all tables and enable pgvector extension"""
    try:
        # Enable pgvector extension
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            logger.info("pgvector extension enabled")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created/verified")
        
    except Exception as e:
        logger.error(f"Failed to create tables: {str(e)}")
        raise

def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_existing_courses():
    """Get courses that have PDF documents available in the post table with Redis caching"""
    # Check cache first
    cached_courses = redis_service.get("courses_with_docs", "json")
    if cached_courses:
        logger.debug("Using cached courses with documents data")
        return cached_courses
    
    db = SessionLocal()
    try:
        # Only get courses that have documents with PDF URLs
        result = db.execute(text("""
            SELECT DISTINCT c.id, c.grade, c.category, c.subject, COUNT(p.id) as doc_count
            FROM courses c
            JOIN post p ON c.id = p.course_id
            WHERE p.doc_url IS NOT NULL
            GROUP BY c.id, c.grade, c.category, c.subject
            HAVING COUNT(p.id) > 0
            ORDER BY c.category, c.grade, c.subject
        """))
        courses = [{"id": row[0], "grade": row[1], "category": row[2], "subject": row[3], "document_count": row[4]} 
                  for row in result.fetchall()]
        
        # Cache for 1 hour (courses don't change frequently)
        redis_service.set("courses_with_docs", courses, ttl=3600)
        
        logger.info(f"Found {len(courses)} courses with PDF documents")
        return courses
    finally:
        db.close()

def get_course_documents(course_id: int):
    """Get all documents for a specific course with Redis caching"""
    # Check cache first
    cached_docs = redis_service.get_cached_course_documents(course_id)
    if cached_docs:
        logger.debug(f"Using cached documents for course {course_id}")
        return cached_docs
    
    db = SessionLocal()
    try:
        result = db.execute(text("""
            SELECT p.id, p.post_name, p.doc_name, p.doc_url, p.details, c.subject, c.grade
            FROM post p
            JOIN courses c ON p.course_id = c.id
            WHERE p.course_id = :course_id AND p.doc_url IS NOT NULL
            ORDER BY p.date DESC
        """), {"course_id": course_id})
        documents = [{"post_id": row[0], "post_name": row[1], "doc_name": row[2], 
                     "doc_url": row[3], "details": row[4], "subject": row[5], "grade": row[6]} 
                     for row in result.fetchall()]
        
        # Cache for 30 minutes
        redis_service.cache_course_documents(course_id, documents)
        
        return documents
    finally:
        db.close()

def get_unindexed_courses():
    """Get courses that haven't been indexed yet or need re-indexing"""
    db = SessionLocal()
    try:
        # Get all courses with documents
        courses_with_docs = db.execute(text("""
            SELECT DISTINCT c.id, c.grade, c.category, c.subject, COUNT(p.id) as doc_count
            FROM courses c
            JOIN post p ON c.id = p.course_id
            WHERE p.doc_url IS NOT NULL
            GROUP BY c.id, c.grade, c.category, c.subject
            ORDER BY c.id
        """)).fetchall()
        
        # Get indexed course statuses
        indexed_courses = db.query(CourseIndexStatus).all()
        indexed_course_ids = {status.course_id for status in indexed_courses if status.status == 'completed'}
        
        # Find unindexed courses
        unindexed = []
        for course in courses_with_docs:
            if course[0] not in indexed_course_ids:
                unindexed.append({
                    "id": course[0],
                    "grade": course[1],
                    "category": course[2],
                    "subject": course[3],
                    "document_count": course[4]
                })
        
        return unindexed
        
    finally:
        db.close()

def get_course_index_status(course_id: int):
    """Get indexing status for a specific course"""
    db = SessionLocal()
    try:
        status = db.query(CourseIndexStatus).filter(
            CourseIndexStatus.course_id == course_id
        ).first()
        return status
    finally:
        db.close()

def update_course_index_status(course_id: int, status: str, document_count: int = 0, 
                              chunk_count: int = 0, error_message: str = None):
    """Update course indexing status"""
    db = SessionLocal()
    try:
        existing_status = db.query(CourseIndexStatus).filter(
            CourseIndexStatus.course_id == course_id
        ).first()
        
        if existing_status:
            existing_status.status = status
            existing_status.document_count = document_count
            existing_status.chunk_count = chunk_count
            existing_status.error_message = error_message
            if status == 'completed':
                existing_status.last_indexed = datetime.utcnow()
        else:
            new_status = CourseIndexStatus(
                course_id=course_id,
                status=status,
                document_count=document_count,
                chunk_count=chunk_count,
                error_message=error_message,
                last_indexed=datetime.utcnow()  # Always set timestamp
            )
            db.add(new_status)
        
        db.commit()
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update course index status: {str(e)}")
        raise
    finally:
        db.close()
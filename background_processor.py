import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import text
import uuid

from document_processor import DocumentProcessor
from vector_store import VectorStore
from redis_service import redis_service

# Configure logging
logger = logging.getLogger(__name__)

class ProcessStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class ProcessInfo:
    process_id: str
    post_id: int
    status: ProcessStatus
    progress: float  # 0-100
    message: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class BackgroundProcessor:
    def __init__(self):
        self.doc_processor = DocumentProcessor()
        self.vector_store = VectorStore()
        self.processes: Dict[str, ProcessInfo] = {}
        self.queue = asyncio.Queue()
        self.is_running = False
        
    async def start(self):
        """Start the background processor"""
        if not self.is_running:
            self.is_running = True
            asyncio.create_task(self._process_queue())
            logger.info("Background processor started")
    
    async def stop(self):
        """Stop the background processor"""
        self.is_running = False
        logger.info("Background processor stopped")
    
    def submit_document_processing(self, post_id: int, db: Session) -> str:
        """Submit a document for processing and return process ID"""
        process_id = str(uuid.uuid4())
        
        # Get document info
        result = db.execute(text("""
            SELECT p.id, p.post_name, p.doc_url, p.doc_name, c.id as course_id, c.subject
            FROM post p 
            JOIN courses c ON p.course_id = c.id 
            WHERE p.id = :post_id
        """), {"post_id": post_id})
        
        post_row = result.fetchone()
        if not post_row:
            raise ValueError(f"Post {post_id} not found")
        
        if not post_row[2] or not post_row[3]:  # doc_url or doc_name
            raise ValueError(f"Post {post_id} has no document to process")
        
        doc_info = {
            'post_id': post_row[0],
            'post_name': post_row[1],
            'doc_url': post_row[2],
            'doc_name': post_row[3],
            'course_id': post_row[4],
            'subject': post_row[5]
        }
        
        # Create process info
        process_info = ProcessInfo(
            process_id=process_id,
            post_id=post_id,
            status=ProcessStatus.QUEUED,
            progress=0.0,
            message="Queued for processing",
            created_at=datetime.now()
        )
        
        self.processes[process_id] = process_info
        
        # Add to queue
        self.queue.put_nowait({
            'process_id': process_id,
            'doc_info': doc_info
        })
        
        logger.info(f"Document processing queued: {process_id} for post {post_id}")
        return process_id
    
    def submit_file_processing(self, post_id: int, course_id: int, file_path: str, doc_name: str, post_name: str) -> str:
        """Submit a file for processing and return process ID"""
        process_id = str(uuid.uuid4())
        
        doc_info = {
            'post_id': post_id,
            'post_name': post_name,
            'file_path': file_path,  # Local file instead of doc_url
            'doc_name': doc_name,
            'course_id': course_id,
            'subject': f"Course {course_id}"
        }
        
        # Create process info
        process_info = ProcessInfo(
            process_id=process_id,
            post_id=post_id,
            status=ProcessStatus.QUEUED,
            progress=0.0,
            message="Queued for processing",
            created_at=datetime.now()
        )
        
        self.processes[process_id] = process_info
        
        # Add to queue
        self.queue.put_nowait({
            'process_id': process_id,
            'doc_info': doc_info
        })
        
        logger.info(f"File processing queued: {process_id} for post {post_id}")
        return process_id
    
    def get_process_status(self, process_id: str) -> Optional[ProcessInfo]:
        """Get the status of a process"""
        return self.processes.get(process_id)
    
    def list_processes(self, post_id: Optional[int] = None) -> Dict[str, ProcessInfo]:
        """List all processes, optionally filtered by post_id"""
        if post_id is None:
            return self.processes
        return {pid: info for pid, info in self.processes.items() if info.post_id == post_id}
    
    async def _process_queue(self):
        """Process the queue of documents"""
        while self.is_running:
            try:
                # Get next item from queue with timeout
                try:
                    item = await asyncio.wait_for(self.queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue
                
                process_id = item['process_id']
                doc_info = item['doc_info']
                
                await self._process_document(process_id, doc_info)
                
            except Exception as e:
                logger.error(f"Error in background processor: {str(e)}")
                await asyncio.sleep(1)
    
    async def _process_document(self, process_id: str, doc_info: dict):
        """Process a single document"""
        process_info = self.processes[process_id]
        
        try:
            # Update status to processing
            process_info.status = ProcessStatus.PROCESSING
            process_info.started_at = datetime.now()
            process_info.message = "Starting document processing"
            process_info.progress = 5.0
            
            logger.info(f"Processing document for post {doc_info['post_id']}: {doc_info['doc_name']}")
            
            # Step 1: Download/read and parse document
            process_info.message = "Processing document"
            process_info.progress = 15.0
            
            # Handle both file_path (uploaded file) and doc_url (remote document)
            if 'file_path' in doc_info:
                processing_result = self.doc_processor.process_document(
                    doc_info['file_path'], 
                    doc_info['doc_name']
                )
            else:
                processing_result = self.doc_processor.process_document(
                    doc_info['doc_url'], 
                    doc_info['doc_name']
                )
            
            if not processing_result['success']:
                raise Exception(f"Failed to process document: {processing_result['error']}")
            
            # Step 2: Generate document summary
            process_info.message = "Generating document summary"
            process_info.progress = 30.0
            
            document_summary = await asyncio.to_thread(
                self.doc_processor.generate_document_summary,
                processing_result['parsed_content'],
                doc_info['doc_name'],
                doc_info['post_name']
            )
            
            # Step 3: Chunk the content
            process_info.message = "Chunking document content"
            process_info.progress = 45.0
            
            chunks = self.doc_processor.chunk_text(processing_result['parsed_content'])
            
            # Step 4: Prepare metadata
            process_info.message = "Preparing chunk metadata"
            process_info.progress = 60.0
            
            metadata_list = []
            for i, chunk in enumerate(chunks):
                metadata_list.append({
                    "post_id": doc_info['post_id'],
                    "course_id": doc_info['course_id'],
                    "doc_name": doc_info['doc_name'],
                    "post_name": doc_info['post_name'],
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })
            
            # Step 5: Store in vector database
            process_info.message = "Storing chunks in vector database"
            process_info.progress = 75.0
            
            await asyncio.to_thread(
                self.vector_store.add_document_chunks,
                chunks, 
                metadata_list
            )
            
            # Step 6: Store document summary
            process_info.message = "Storing document summary"
            process_info.progress = 90.0
            
            await asyncio.to_thread(
                self.vector_store.store_document_summary,
                doc_info['post_id'],
                doc_info['course_id'],
                doc_info['doc_name'],
                doc_info['post_name'],
                document_summary
            )
            
            # Step 7: Invalidate cache
            process_info.message = "Updating cache"
            process_info.progress = 95.0
            
            redis_service.invalidate_course_cache(doc_info['course_id'])
            
            # Complete
            process_info.status = ProcessStatus.COMPLETED
            process_info.progress = 100.0
            process_info.message = f"Successfully processed {len(chunks)} chunks"
            process_info.completed_at = datetime.now()
            
            logger.info(f"Successfully processed document for post {doc_info['post_id']}: {len(chunks)} chunks")
            
        except Exception as e:
            logger.error(f"Error processing document for post {doc_info['post_id']}: {str(e)}")
            
            process_info.status = ProcessStatus.FAILED
            process_info.error_message = str(e)
            process_info.message = f"Processing failed: {str(e)}"
            process_info.completed_at = datetime.now()

# Global instance
background_processor = BackgroundProcessor()
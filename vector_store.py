import os
import hashlib
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from openai import OpenAI
from typing import List, Dict, Any, Optional
import logging
from dotenv import load_dotenv
from models import DocumentChunk, DocumentSummary
from redis_service import redis_service

load_dotenv()

logger = logging.getLogger(__name__)

class VectorStore:
    def __init__(self):
        # Database connection
        self.database_url = os.getenv("DATABASE_URL")
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Initialize OpenAI client for embeddings
        self.openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        # Using text-embedding-3-large for better accuracy on educational content
        # 10-15% improvement over text-embedding-3-small for academic/technical material
        self.embedding_model = "text-embedding-3-large"
        self.embedding_dim = 3072  # text-embedding-3-large produces 3072-dimensional embeddings
    
    def enhance_chunk_for_embedding(self, chunk: str, metadata: Dict[str, Any]) -> str:
        """
        Enhance chunk with educational metadata before embedding.
        This provides better context-aware embeddings for improved retrieval.

        Args:
            chunk: Raw text chunk
            metadata: Contains subject, topic, page_number, doc_name, etc.

        Returns:
            Enhanced text with metadata prefix
        """
        # Extract metadata
        subject = metadata.get('subject', '')
        doc_name = metadata.get('doc_name', '')
        post_name = metadata.get('post_name', '')
        page_num = metadata.get('page_number', '')

        # Extract potential topic from doc_name (e.g., "Chapter_5_Photosynthesis.pdf" -> "Photosynthesis")
        topic = ''
        if doc_name:
            # Remove common patterns and extract topic
            topic = doc_name.replace('.pdf', '').replace('_', ' ').replace('-', ' ')

        # Build enhanced text with educational context
        enhanced_parts = []

        if subject:
            enhanced_parts.append(f"Subject: {subject}")

        if topic:
            enhanced_parts.append(f"Topic: {topic}")

        if page_num:
            enhanced_parts.append(f"Page: {page_num}")

        # Add the actual content
        enhanced_parts.append(f"Content: {chunk}")

        enhanced_text = "\n".join(enhanced_parts)

        logger.debug(f"Enhanced chunk with metadata - Subject: {subject}, Topic: {topic}")
        return enhanced_text

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI's text-embedding-3-large with Redis caching"""
        embeddings = []
        texts_to_generate = []
        cache_keys = []

        # Check cache for each text
        for text in texts:
            cached_embedding = redis_service.get_cached_embedding(text)
            if cached_embedding:
                embeddings.append(cached_embedding)
                cache_keys.append(None)  # Mark as cached
                logger.debug(f"Using cached embedding for text (length: {len(text)})")
            else:
                embeddings.append(None)  # Placeholder
                texts_to_generate.append(text)
                cache_keys.append(text)  # Mark for generation
        
        # Generate embeddings for uncached texts
        if texts_to_generate:
            try:
                logger.info(f"Generating {len(texts_to_generate)} new embeddings via OpenAI API")
                response = self.openai_client.embeddings.create(
                    model=self.embedding_model,
                    input=texts_to_generate,
                    encoding_format="float"
                )
                
                generated_embeddings = [embedding.embedding for embedding in response.data]
                
                # Fill in the generated embeddings and cache them
                gen_index = 0
                for i, cache_key in enumerate(cache_keys):
                    if cache_key is not None:  # This was not cached
                        embedding = generated_embeddings[gen_index]
                        embeddings[i] = embedding
                        
                        # Cache the embedding
                        redis_service.cache_embedding(cache_key, embedding)
                        gen_index += 1
                
            except Exception as e:
                logger.error(f"Failed to generate embeddings: {str(e)}")
                raise
        
        return embeddings

    def add_document_chunks(self, chunks: List[str], metadata_list: List[Dict[str, Any]]) -> bool:
        """
        Add document chunks to pgvector database with enhanced embeddings.

        Now includes metadata enhancement for better educational content retrieval:
        - Subject context for better cross-subject differentiation
        - Topic extraction from document names
        - Page numbers for spatial context
        """
        db = self.SessionLocal()
        try:
            # Enhance chunks with metadata before generating embeddings
            enhanced_chunks = []
            for chunk, metadata in zip(chunks, metadata_list):
                enhanced_chunk = self.enhance_chunk_for_embedding(chunk, metadata)
                enhanced_chunks.append(enhanced_chunk)

            logger.info(f"Enhanced {len(chunks)} chunks with educational metadata")

            # Generate embeddings using enhanced text
            embeddings = self.generate_embeddings(enhanced_chunks)

            # Create DocumentChunk objects
            chunk_objects = []
            for i, (chunk, metadata) in enumerate(zip(chunks, metadata_list)):
                chunk_obj = DocumentChunk(
                    post_id=metadata['post_id'],
                    course_id=metadata['course_id'],
                    doc_name=metadata['doc_name'],
                    post_name=metadata.get('post_name', ''),
                    chunk_text=chunk,
                    chunk_index=metadata['chunk_index'],
                    total_chunks=metadata['total_chunks'],
                    page_number=metadata.get('page_number'),  # Add page number
                    embedding=embeddings[i]
                )
                chunk_objects.append(chunk_obj)

            # Add all chunks to database
            db.add_all(chunk_objects)
            db.commit()

            logger.info(f"Added {len(chunks)} chunks to pgvector database")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to add chunks to vector store: {str(e)}")
            return False
        finally:
            db.close()
    
    def enhance_query_for_search(self, query: str, subject: Optional[str] = None,
                                 topic: Optional[str] = None) -> str:
        """
        Enhance user query with subject context to match enhanced chunk embeddings.
        This ensures query and chunks are embedded in the same semantic space.
        """
        enhanced_parts = []

        if subject:
            enhanced_parts.append(f"Subject: {subject}")

        if topic:
            enhanced_parts.append(f"Topic: {topic}")

        # Add the actual query
        enhanced_parts.append(f"Content: {query}")

        return "\n".join(enhanced_parts)

    def search_similar_chunks(self, query: str, course_id: Optional[int] = None,
                            post_id: Optional[int] = None, n_results: int = 5,
                            similarity_threshold: float = 0.5,
                            subject: Optional[str] = None,
                            topic: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks using pgvector cosine similarity.

        Now supports enhanced queries with subject/topic context for better matching
        with metadata-enhanced chunk embeddings.
        """
        # Enhance query with subject context if provided
        enhanced_query = query
        if subject or topic:
            enhanced_query = self.enhance_query_for_search(query, subject, topic)
            logger.info(f"Enhanced query with subject context: {subject}")

        # Create cache key for this search
        query_hash = hashlib.md5(f"{enhanced_query}:{n_results}".encode()).hexdigest()

        # Check cache first (use post_id or course_id for caching)
        cache_id = post_id if post_id else (course_id or 0)
        cached_results = redis_service.get_cached_similarity_search(query_hash, cache_id)
        if cached_results:
            logger.debug(f"Using cached similarity search results for query hash: {query_hash}")
            return cached_results

        db = self.SessionLocal()
        try:
            # Generate query embedding using enhanced query (with caching)
            query_embeddings = self.generate_embeddings([enhanced_query])
            query_embedding = query_embeddings[0]
            
            # Build SQL query with pgvector similarity search
            # Convert embedding list to string format for PostgreSQL vector type
            embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
            
            if post_id:
                # Filter by post_id
                sql_query = text(f"""
                    SELECT chunk_text, post_id, course_id, doc_name, post_name,
                           chunk_index, total_chunks, page_number,
                           1 - (embedding <=> '{embedding_str}'::vector) as similarity_score
                    FROM document_chunks
                    WHERE post_id = :post_id
                    ORDER BY embedding <=> '{embedding_str}'::vector
                    LIMIT :n_results
                """)
                result = db.execute(sql_query, {
                    "post_id": post_id,
                    "n_results": n_results
                })
            elif course_id:
                # Use string formatting to avoid parameter binding issues with vector type
                sql_query = text(f"""
                    SELECT chunk_text, post_id, course_id, doc_name, post_name,
                           chunk_index, total_chunks, page_number,
                           1 - (embedding <=> '{embedding_str}'::vector) as similarity_score
                    FROM document_chunks
                    WHERE course_id = :course_id
                    ORDER BY embedding <=> '{embedding_str}'::vector
                    LIMIT :n_results
                """)
                result = db.execute(sql_query, {
                    "course_id": course_id,
                    "n_results": n_results
                })
            else:
                sql_query = text(f"""
                    SELECT chunk_text, post_id, course_id, doc_name, post_name,
                           chunk_index, total_chunks, page_number,
                           1 - (embedding <=> '{embedding_str}'::vector) as similarity_score
                    FROM document_chunks
                    ORDER BY embedding <=> '{embedding_str}'::vector
                    LIMIT :n_results
                """)
                result = db.execute(sql_query, {
                    "n_results": n_results
                })

            # Format results
            formatted_results = []
            for row in result.fetchall():
                formatted_results.append({
                    "content": row[0],
                    "metadata": {
                        "post_id": row[1],
                        "course_id": row[2],
                        "doc_name": row[3],
                        "post_name": row[4],
                        "chunk_index": row[5],
                        "total_chunks": row[6],
                        "page_number": row[7]  # Add page number to metadata
                    },
                    "similarity_score": float(row[8])  # Updated index
                })
            
            # Cache the results
            redis_service.cache_similarity_search(query_hash, cache_id, formatted_results)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
        finally:
            db.close()
    
    def get_course_document_count(self, course_id: int) -> int:
        """Get number of document chunks for a specific course"""
        db = self.SessionLocal()
        try:
            count = db.query(DocumentChunk).filter(
                DocumentChunk.course_id == course_id
            ).count()
            return count
        except Exception as e:
            logger.error(f"Failed to get document count: {str(e)}")
            return 0
        finally:
            db.close()
    
    def get_post_document_count(self, post_id: int) -> int:
        """Get number of document chunks for a specific post"""
        db = self.SessionLocal()
        try:
            count = db.query(DocumentChunk).filter(
                DocumentChunk.post_id == post_id
            ).count()
            return count
        except Exception as e:
            logger.error(f"Failed to get document count for post {post_id}: {str(e)}")
            return 0
        finally:
            db.close()
    
    def delete_document_chunks(self, post_id: int) -> bool:
        """Delete all chunks for a specific document"""
        db = self.SessionLocal()
        try:
            # Delete all chunks for this post
            deleted_count = db.query(DocumentChunk).filter(
                DocumentChunk.post_id == post_id
            ).delete()
            
            db.commit()
            logger.info(f"Deleted {deleted_count} chunks for post {post_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to delete chunks for post {post_id}: {str(e)}")
            return False
        finally:
            db.close()
    
    def store_document_summary(self, post_id: int, course_id: int, doc_name: str, post_name: str, summary: str) -> bool:
        """Store document summary in the database"""
        db = self.SessionLocal()
        try:
            # Check if summary already exists
            existing_summary = db.query(DocumentSummary).filter(DocumentSummary.post_id == post_id).first()
            
            if existing_summary:
                # Update existing summary
                existing_summary.summary = summary
                existing_summary.doc_name = doc_name
                existing_summary.post_name = post_name
                logger.info(f"Updated summary for post {post_id}")
            else:
                # Create new summary
                new_summary = DocumentSummary(
                    post_id=post_id,
                    course_id=course_id,
                    doc_name=doc_name,
                    post_name=post_name,
                    summary=summary
                )
                db.add(new_summary)
                logger.info(f"Created new summary for post {post_id}")
            
            db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Failed to store document summary for post {post_id}: {str(e)}")
            db.rollback()
            return False
        finally:
            db.close()
    
    def get_document_summary(self, post_id: int) -> Optional[str]:
        """Retrieve document summary for a specific post"""
        db = self.SessionLocal()
        try:
            summary_record = db.query(DocumentSummary).filter(DocumentSummary.post_id == post_id).first()
            if summary_record:
                return summary_record.summary
            return None
        except Exception as e:
            logger.error(f"Failed to get document summary for post {post_id}: {str(e)}")
            return None
        finally:
            db.close()
    
    def get_total_chunks_count(self) -> int:
        """Get total number of chunks in the database"""
        db = self.SessionLocal()
        try:
            count = db.query(DocumentChunk).count()
            return count
        except Exception as e:
            logger.error(f"Failed to get total chunks count: {str(e)}")
            return 0
        finally:
            db.close()
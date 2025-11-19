#!/usr/bin/env python3
"""
Debug script to check course content
"""
import sys
import os
sys.path.append('/app')  # Add app directory to path

from database import get_course_documents, SessionLocal
from models import DocumentChunk
from sqlalchemy import text

def check_course_content():
    print("🔍 Checking Course 178 Content")
    print("=" * 40)
    
    # Check documents
    try:
        docs = get_course_documents(178)
        print(f"\n📚 Documents ({len(docs['documents'])} found):")
        for doc in docs['documents']:
            print(f"  - Name: {doc['doc_name']}")
            print(f"    URL: {doc['doc_url'][:80]}...")
            print(f"    Status: {doc.get('embedding_status', 'unknown')}")
    except Exception as e:
        print(f"❌ Error getting documents: {e}")
    
    # Check chunks
    db = SessionLocal()
    try:
        chunks = db.query(DocumentChunk).filter(
            DocumentChunk.course_id == 178
        ).limit(3).all()
        
        print(f"\n📝 Sample chunks ({len(chunks)} shown):")
        for i, chunk in enumerate(chunks, 1):
            print(f"\n  Chunk {i}:")
            print(f"    Doc: {chunk.doc_name}")
            print(f"    Text preview: {chunk.chunk_text[:100]}...")
            
    except Exception as e:
        print(f"❌ Error getting chunks: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    check_course_content()

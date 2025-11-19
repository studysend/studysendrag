#!/usr/bin/env python3
"""
Migration script to add post_id column to chat_sessions table
"""

from database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_add_post_id():
    """Add post_id column to chat_sessions table"""
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # Check if post_id column already exists
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'chat_sessions' AND column_name = 'post_id'
            """))
            
            if result.fetchone():
                logger.info("post_id column already exists in chat_sessions table")
                trans.commit()
                return
            
            # Add post_id column
            logger.info("Adding post_id column to chat_sessions table")
            conn.execute(text("""
                ALTER TABLE chat_sessions 
                ADD COLUMN post_id INTEGER
            """))
            
            # Create index on post_id
            logger.info("Creating index on post_id column")
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS ix_chat_sessions_post_id 
                ON chat_sessions (post_id)
            """))
            
            trans.commit()
            logger.info("Migration completed successfully")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_add_post_id()

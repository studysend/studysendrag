-- Migration: Upgrade embedding dimensions from 1536 to 3072
-- Purpose: Support text-embedding-3-large for better educational content accuracy
-- Date: 2025-11-30

-- IMPORTANT: This migration requires re-generating embeddings for existing documents
-- The old 1536-dim embeddings are incompatible with new 3072-dim model

-- Step 1: Create new column for 3072-dimensional embeddings
ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS embedding_large vector(3072);

-- Step 2: (Optional) Keep old embeddings for rollback capability
-- If you want to preserve old embeddings temporarily, rename the column:
-- ALTER TABLE document_chunks RENAME COLUMN embedding TO embedding_small;
-- Then recreate embedding as the new large version:
-- ALTER TABLE document_chunks ADD COLUMN embedding vector(3072);

-- Step 3: Drop old embedding column (ONLY after re-indexing all documents!)
-- ALTER TABLE document_chunks DROP COLUMN embedding;
-- ALTER TABLE document_chunks RENAME COLUMN embedding_large TO embedding;

-- Step 4: Update pgvector index for new dimensions
DROP INDEX IF EXISTS idx_document_chunks_embedding;
CREATE INDEX idx_document_chunks_embedding_large
ON document_chunks USING ivfflat (embedding_large vector_cosine_ops)
WITH (lists = 100);

-- For now, we'll use embedding_large as the new column
-- This allows gradual migration without breaking existing data

COMMENT ON COLUMN document_chunks.embedding_large IS '3072-dimensional embeddings from text-embedding-3-large model for better educational content accuracy';

-- Migration Steps After Running This SQL:
-- 1. Update your code to use text-embedding-3-large
-- 2. Re-process all existing documents to generate new embeddings
-- 3. Once all documents are migrated, run Step 3 above to clean up
-- 4. Monitor performance and accuracy improvements

-- Rollback Plan:
-- To rollback, simply:
-- 1. Revert code to use text-embedding-3-small
-- 2. DROP COLUMN embedding_large
-- 3. Keep using original embedding column

-- Migration script to add page_number column to document_chunks table
-- Run this on your PostgreSQL database

-- Add page_number column to document_chunks table
ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS page_number INTEGER;

-- Add index on page_number for faster queries
CREATE INDEX IF NOT EXISTS idx_document_chunks_page_number
ON document_chunks(page_number);

-- Update comment on the column
COMMENT ON COLUMN document_chunks.page_number IS 'Page number where this chunk appears in the original PDF document';

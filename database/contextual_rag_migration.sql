-- Database Migration for Contextual RAG System
-- Add new columns to document_chunks table and create new table for summary embeddings

-- Migration 1: Add contextual fields to document_chunks
-- If these columns don't exist, add them:

-- Check if columns exist first:
-- SELECT column_name FROM information_schema.columns 
-- WHERE table_name='document_chunks' AND column_name='summary';

-- Add columns (safe to run multiple times with IF NOT EXISTS pattern):
ALTER TABLE document_chunks
ADD COLUMN IF NOT EXISTS summary TEXT,
ADD COLUMN IF NOT EXISTS topic VARCHAR(255),
ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP;

-- Create index for faster topic searches
CREATE INDEX IF NOT EXISTS idx_document_chunks_topic 
ON document_chunks(topic);

CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_processed 
ON document_chunks(doc_id, processed_at);

-- Migration 2: Create new table for summary embeddings
CREATE TABLE IF NOT EXISTS chunk_summary_embeddings (
    summary_embedding_id SERIAL PRIMARY KEY,
    chunk_id INTEGER NOT NULL UNIQUE,
    summary_embedding BYTEA NOT NULL,
    embedding_model VARCHAR(100) DEFAULT 'text-embedding-3-small',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_chunk_summary_embeddings_chunk_id 
        FOREIGN KEY (chunk_id) 
        REFERENCES document_chunks(chunk_id) 
        ON DELETE CASCADE
);

-- Create index for summary embedding lookups
CREATE INDEX IF NOT EXISTS idx_chunk_summary_embeddings_chunk_id 
ON chunk_summary_embeddings(chunk_id);

-- Verify the schema
SELECT 
    column_name, 
    data_type, 
    is_nullable
FROM information_schema.columns
WHERE table_name = 'document_chunks'
ORDER BY ordinal_position;

-- Verify relationships
SELECT 
    kcu.column_name,
    ccu.table_name,
    ccu.column_name
FROM information_schema.key_column_usage AS kcu
JOIN information_schema.constraint_column_usage AS ccu
    ON kcu.constraint_name = ccu.constraint_name
WHERE kcu.table_name = 'chunk_summary_embeddings';

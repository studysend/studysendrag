-- Initialize RAG Study Chat Database
-- This script sets up the database with required extensions and initial data

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create initial tables (these will also be created by SQLAlchemy, but this ensures they exist)
-- Note: The actual table creation is handled by the application's models.py

-- Create indexes for better performance
-- These will be created after the application starts and creates tables

-- Insert sample data if needed (optional)
-- You can add sample courses, users, etc. here

-- Set up database permissions
GRANT ALL PRIVILEGES ON DATABASE ragchat TO raguser;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO raguser;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO raguser;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'RAG Study Chat database initialized successfully';
END $$;
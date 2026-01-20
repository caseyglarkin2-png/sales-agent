-- Initialize pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create initial database objects
SELECT 'pgvector extension enabled' as status;

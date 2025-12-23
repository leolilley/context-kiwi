-- Migration: Add PostgreSQL Full-Text Search Support
-- Description: Adds tsvector column and GIN index for fast, scalable full-text search
-- Date: 2024
-- 
-- This migration enables PostgreSQL's native full-text search capabilities,
-- providing better performance and relevance than simple ILIKE pattern matching.
--
-- Benefits:
-- - Faster searches on large datasets
-- - Better relevance ranking
-- - Support for stemming and language-specific search
-- - Scales to millions of directives

-- Step 1: Add search_vector column (auto-updated tsvector)
-- This column automatically indexes name + description for full-text search
ALTER TABLE directives 
ADD COLUMN IF NOT EXISTS search_vector tsvector 
GENERATED ALWAYS AS (
  to_tsvector('english', 
    coalesce(name, '') || ' ' || 
    coalesce(description, '')
  )
) STORED;

-- Step 2: Create GIN index for fast full-text search
-- GIN (Generalized Inverted Index) is optimized for tsvector queries
CREATE INDEX IF NOT EXISTS directives_search_idx 
ON directives 
USING GIN(search_vector);

-- Step 3: Add index on name for exact/prefix matching (complementary to full-text)
CREATE INDEX IF NOT EXISTS directives_name_idx 
ON directives 
USING btree(lower(name));

-- Step 4: Optional - Add index on description for additional search patterns
CREATE INDEX IF NOT EXISTS directives_description_idx 
ON directives 
USING gin(to_tsvector('english', coalesce(description, '')));

-- Usage Example (for future RPC function):
-- 
-- CREATE OR REPLACE FUNCTION search_directives(query_text text, limit_count int DEFAULT 10)
-- RETURNS TABLE (
--   id uuid,
--   name text,
--   description text,
--   category text,
--   relevance real
-- ) AS $$
-- BEGIN
--   RETURN QUERY
--   SELECT 
--     d.id,
--     d.name,
--     d.description,
--     d.category,
--     ts_rank(d.search_vector, plainto_tsquery('english', query_text)) as relevance
--   FROM directives d
--   WHERE d.search_vector @@ plainto_tsquery('english', query_text)
--   ORDER BY relevance DESC
--   LIMIT limit_count;
-- END;
-- $$ LANGUAGE plpgsql;

-- Verification:
-- SELECT 
--   name, 
--   description,
--   search_vector,
--   ts_rank(search_vector, plainto_tsquery('english', 'auth')) as rank
-- FROM directives
-- WHERE search_vector @@ plainto_tsquery('english', 'auth')
-- ORDER BY rank DESC
-- LIMIT 5;



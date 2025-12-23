-- Migration: Add tags column to directives table
-- Date: 2025-12-09
-- Description: Adds tags support for better directive categorization and filtering
-- Status: APPLIED - 2025-12-09

-- ============================================================================
-- STEP 1: Add tags column (JSONB array)
-- ============================================================================
-- ALTER TABLE public.directives 
-- ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;

-- ============================================================================
-- STEP 2: Add index on tags for filtering
-- ============================================================================
-- CREATE INDEX IF NOT EXISTS idx_directives_tags 
-- ON public.directives USING GIN(tags);

-- ============================================================================
-- STEP 3: Add comment
-- ============================================================================
-- COMMENT ON COLUMN public.directives.tags IS 
-- 'Array of tag strings for additional categorization and filtering';

-- ============================================================================
-- NOTES
-- ============================================================================
-- This migration is reserved for future use.
-- Currently, tags filtering is disabled in the search code.
-- When ready to enable tags:
-- 1. Run this migration
-- 2. Update context_kiwi/db/directives.py to uncomment tags references
-- 3. Update publish tool to extract tags from directive metadata
-- 4. Update search tool to enable tags filtering

-- Example usage after migration:
-- SELECT * FROM directives WHERE tags @> '["react", "typescript"]'::jsonb;
-- SELECT * FROM directives WHERE tags ? 'authentication';

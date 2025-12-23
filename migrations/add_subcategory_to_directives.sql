-- Migration: Add subcategory support and remove category CHECK constraint
-- Date: 2025-01-27
-- Description: Aligns context-kiwi with script-kiwi's dynamic category system

-- ============================================================================
-- STEP 1: Add subcategory column (nullable)
-- ============================================================================
ALTER TABLE public.directives 
ADD COLUMN IF NOT EXISTS subcategory TEXT;

-- ============================================================================
-- STEP 2: Remove CHECK constraint on category
-- ============================================================================
-- First, drop the existing constraint
ALTER TABLE public.directives 
DROP CONSTRAINT IF EXISTS directives_category_check;

-- ============================================================================
-- STEP 3: Add index on subcategory for filtering
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_directives_subcategory 
ON public.directives USING btree (subcategory);

-- ============================================================================
-- STEP 4: Update existing data (optional - keep existing categories as-is)
-- ============================================================================
-- No data migration needed - existing categories remain valid
-- New directives can use any category name

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- Verify the changes:
-- SELECT column_name, data_type, is_nullable 
-- FROM information_schema.columns 
-- WHERE table_name = 'directives' AND column_name IN ('category', 'subcategory');
--
-- Should show:
-- category: TEXT, NOT NULL (no CHECK constraint)
-- subcategory: TEXT, nullable


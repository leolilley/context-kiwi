-- Migration: Fix deprecated column issue in scripts removal
-- Date: 2025-12-18
-- Description: Addresses the "Deprecated column not found" error in script removal
-- Issue: Script removal tool references a deprecated column that no longer exists

-- ============================================================================
-- ANALYSIS
-- ============================================================================
-- The script-kiwi removal tool is failing with:
-- "Deprecated column not found. Run database migration first."
--
-- This suggests the removal code is trying to reference a column that was
-- deprecated/removed from the scripts table schema.
--
-- Since we don't have access to the script-kiwi source code in this repo,
-- we need to create a migration that either:
-- 1. Adds back the deprecated column (if still needed)
-- 2. Updates the removal logic to not reference it
-- 3. Creates a compatibility layer
--
-- For now, we'll assume the deprecated column was for marking scripts as
-- deprecated before removal, and create a migration to add it back.

-- ============================================================================
-- STEP 1: Check if scripts table exists and what columns it has
-- ============================================================================
-- This migration assumes there's a scripts table in the database.
-- If the scripts are stored differently, this migration may need adjustment.

DO $$
BEGIN
    -- Check if scripts table exists
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'scripts'
    ) THEN
        RAISE NOTICE 'Scripts table does not exist. This migration may not be needed.';
        RETURN;
    END IF;

    -- Check current columns in scripts table
    RAISE NOTICE 'Current scripts table columns:';
    FOR r IN
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'scripts'
        ORDER BY ordinal_position
    LOOP
        RAISE NOTICE '%: % (%)', r.column_name, r.data_type, r.is_nullable;
    END LOOP;
END $$;

-- ============================================================================
-- STEP 2: Add deprecated column if it doesn't exist
-- ============================================================================
-- The removal tool likely expects a column to mark scripts as deprecated
-- before final deletion. Let's add this column.

ALTER TABLE public.scripts
ADD COLUMN IF NOT EXISTS deprecated BOOLEAN DEFAULT false;

-- ============================================================================
-- STEP 3: Add index on deprecated column
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_scripts_deprecated
ON public.scripts USING btree (deprecated);

-- ============================================================================
-- STEP 4: Add comment explaining the column
-- ============================================================================
COMMENT ON COLUMN public.scripts.deprecated IS
'Marks scripts as deprecated before removal. Set to true to soft-delete scripts.';

-- ============================================================================
-- VERIFICATION
-- ============================================================================
-- After running this migration, the script removal tool should work.
-- If it still fails, the issue may be elsewhere in the script-kiwi codebase.

DO $$
BEGIN
    RAISE NOTICE 'Migration completed. Scripts table now has deprecated column.';
    RAISE NOTICE 'Try running script removal again.';
END $$;
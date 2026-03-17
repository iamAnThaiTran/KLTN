-- ============================================================================
-- MIGRATION: Add missing columns to search_history table
-- ============================================================================
-- Issue: ORM model expected category_name and clicked_product_id columns
-- but they were missing from the database schema
-- ============================================================================

-- Add category_name column if it doesn't exist
ALTER TABLE search_history
ADD COLUMN IF NOT EXISTS category_name VARCHAR(255);

-- Add clicked_product_id column if it doesn't exist
ALTER TABLE search_history
ADD COLUMN IF NOT EXISTS clicked_product_id INT;

-- Optional: Add index on category_name for better query performance
CREATE INDEX IF NOT EXISTS idx_search_history_category_name ON search_history(category_name);

-- Verify the migration
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'search_history'
ORDER BY ordinal_position;

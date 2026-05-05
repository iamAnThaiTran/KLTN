-- Migration: Add recommendation-related fields to SKU table
-- Purpose: Support trending products, ratings, and search count for recommendation engine
-- Database: products_db

\c products_db

-- ============================================================================
-- Add columns to skus table for recommendation features
-- ============================================================================

ALTER TABLE skus
ADD COLUMN search_count INTEGER DEFAULT 0,
ADD COLUMN rating DECIMAL(3, 2) DEFAULT 0;

-- ============================================================================
-- Create indexes for recommendation queries
-- ============================================================================

CREATE INDEX idx_skus_search_count ON skus(search_count DESC);
CREATE INDEX idx_skus_rating ON skus(rating DESC);
CREATE INDEX idx_skus_rating_search ON skus(rating DESC, search_count DESC);

-- ============================================================================
-- Verification
-- ============================================================================

-- Check new columns
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'skus'
ORDER BY ordinal_position;

-- Check new indexes
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'skus' AND indexname LIKE 'idx_skus_%'
ORDER BY indexname;

-- Migration: Add Many-to-Many Product-Category Relationship
-- This migration adds schema evolution support for category attributes

-- ============================================================================
-- Add schema versioning to categories
-- ============================================================================

ALTER TABLE categories ADD COLUMN IF NOT EXISTS schema_version INTEGER DEFAULT 1;
ALTER TABLE categories ADD COLUMN IF NOT EXISTS last_updated_attributes TIMESTAMP DEFAULT CURRENT_TIMESTAMP;

-- ============================================================================
-- Add schema tracking to products
-- ============================================================================

ALTER TABLE products ADD COLUMN IF NOT EXISTS last_schema_version INTEGER DEFAULT 1;

-- ============================================================================
-- Create product_categories many-to-many mapping table
-- ============================================================================

CREATE TABLE IF NOT EXISTS product_categories (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, category_id)
);

-- ============================================================================
-- Create triggers for backward compatibility
-- ============================================================================

-- When updating product.category_id (legacy), sync product_categories table
CREATE OR REPLACE FUNCTION sync_product_categories_on_legacy_update()
RETURNS TRIGGER AS $$
BEGIN
    -- If category_id changed, update product_categories
    IF NEW.category_id IS NOT NULL AND (OLD.category_id IS NULL OR OLD.category_id != NEW.category_id) THEN
        -- Remove old primary
        UPDATE product_categories SET is_primary = FALSE WHERE product_id = NEW.id;
        
        -- Add or update new primary
        INSERT INTO product_categories (product_id, category_id, is_primary)
        VALUES (NEW.id, NEW.category_id, TRUE)
        ON CONFLICT (product_id, category_id) DO UPDATE
        SET is_primary = TRUE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF NOT EXISTS sync_product_categories_trigger ON products;
CREATE TRIGGER sync_product_categories_trigger
AFTER UPDATE ON products
FOR EACH ROW
EXECUTE FUNCTION sync_product_categories_on_legacy_update();

-- ============================================================================
-- Create indexes for product_categories
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_product_categories_product ON product_categories(product_id);
CREATE INDEX IF NOT EXISTS idx_product_categories_category ON product_categories(category_id);
CREATE INDEX IF NOT EXISTS idx_product_categories_primary ON product_categories(product_id, is_primary);

-- ============================================================================
-- Migrate existing data to product_categories
-- ============================================================================

-- For each product, create mapping to its category_id
INSERT INTO product_categories (product_id, category_id, is_primary)
SELECT id, category_id, TRUE FROM products
WHERE category_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- ============================================================================
-- Add comment for documentation
-- ============================================================================

COMMENT ON TABLE product_categories IS 'Many-to-many relationship between products and categories for multi-category support';
COMMENT ON COLUMN product_categories.is_primary IS 'Whether this is the primary category for the product (for backward compatibility)';
COMMENT ON COLUMN categories.schema_version IS 'Version of category schema for tracking attribute changes';
COMMENT ON COLUMN categories.last_updated_attributes IS 'Timestamp when attributes were last updated';
COMMENT ON COLUMN products.last_schema_version IS 'Last schema version of category that product was synced with';

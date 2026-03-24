-- Migration: Thêm Tiki external IDs vào bảng products
-- Created: 2026-03-24
-- Purpose: Lưu tiki_product_id, tiki_spid, seller_id để dùng cho review crawler

-- ============================================================================
-- THÊM CỘT VÀO BẢNG PRODUCTS
-- ============================================================================

-- Thêm cột tiki_product_id
ALTER TABLE products ADD COLUMN IF NOT EXISTS tiki_product_id VARCHAR(100);

-- Thêm cột tiki_spid
ALTER TABLE products ADD COLUMN IF NOT EXISTS tiki_spid VARCHAR(100);

-- Thêm cột seller_id
ALTER TABLE products ADD COLUMN IF NOT EXISTS seller_id VARCHAR(100) DEFAULT '1';

-- ============================================================================
-- THÊM INDEX ĐỂ OPTIMIZE QUERIES
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_products_tiki_id ON products(tiki_product_id);
CREATE INDEX IF NOT EXISTS idx_products_tiki_spid ON products(tiki_spid);

-- ============================================================================
-- THÊM COMMENTS
-- ============================================================================

COMMENT ON COLUMN products.tiki_product_id IS 'Tiki external product ID (e.g., 16268021)';
COMMENT ON COLUMN products.tiki_spid IS 'Tiki SKU/variant ID (e.g., 16268022)';
COMMENT ON COLUMN products.seller_id IS 'Tiki seller ID (default: 1 for main store)';

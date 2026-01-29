-- ============================================================================
-- SKU-BASED PRODUCT SCHEMA FOR ASSISTED SHOPPING
-- ============================================================================
-- Design:
--   - Products are generic items (e.g., "Nike Air Max 2024")
--   - SKUs are variants with specific attributes (e.g., Size 42, Color Red)
--   - Attributes are stored flexibly in key-value format
-- ============================================================================

-- Drop existing tables (if recreating)
DROP TABLE IF EXISTS sku_attributes CASCADE;
DROP TABLE IF EXISTS skus CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS category_attributes CASCADE;
DROP TABLE IF EXISTS categories CASCADE;

-- ============================================================================
-- 1. CATEGORIES TABLE
-- ============================================================================
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_categories_slug ON categories(slug);

COMMENT ON TABLE categories IS 'Product categories (e.g., shoes, laptops, watches)';

-- ============================================================================
-- 2. CATEGORY_ATTRIBUTES TABLE
-- ============================================================================
-- Defines which attributes are available for each category
CREATE TABLE category_attributes (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    data_type VARCHAR(50) DEFAULT 'text',  -- text, number, enum, range
    possible_values JSONB,  -- For enum types: ["red", "blue", "green"]
    is_required BOOLEAN DEFAULT FALSE,
    is_filterable BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, name)
);

CREATE INDEX idx_category_attributes_category ON category_attributes(category_id);
CREATE INDEX idx_category_attributes_filterable ON category_attributes(category_id, is_filterable);

COMMENT ON TABLE category_attributes IS 'Attribute schema for each category';
COMMENT ON COLUMN category_attributes.data_type IS 'Type: text, number, enum, range';
COMMENT ON COLUMN category_attributes.possible_values IS 'For enum: list of valid values';

-- ============================================================================
-- 3. PRODUCTS TABLE
-- ============================================================================
-- Generic product without variant-specific attributes
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    brand VARCHAR(100),
    description TEXT,
    product_url TEXT,
    thumbnail VARCHAR(500),
    source VARCHAR(50),  -- tiki, lazada, shopee
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_source ON products(source);
CREATE INDEX idx_products_active ON products(is_active);

COMMENT ON TABLE products IS 'Generic products without variant attributes';

-- ============================================================================
-- 4. SKUS TABLE (Stock Keeping Units)
-- ============================================================================
-- Product variants with specific attributes
CREATE TABLE skus (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku_code VARCHAR(100) UNIQUE,
    price DECIMAL(12, 2) NOT NULL,
    original_price DECIMAL(12, 2),
    stock INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skus_product ON skus(product_id);
CREATE INDEX idx_skus_price ON skus(price);
CREATE INDEX idx_skus_available ON skus(is_available);
CREATE INDEX idx_skus_code ON skus(sku_code);

COMMENT ON TABLE skus IS 'Product variants with specific attributes';

-- ============================================================================
-- 5. SKU_ATTRIBUTES TABLE
-- ============================================================================
-- Flexible key-value storage for SKU attributes
CREATE TABLE sku_attributes (
    sku_id INTEGER NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value TEXT NOT NULL,
    PRIMARY KEY (sku_id, attribute_name)
);

CREATE INDEX idx_sku_attrs_name ON sku_attributes(attribute_name);
CREATE INDEX idx_sku_attrs_value ON sku_attributes(attribute_value);
CREATE INDEX idx_sku_attrs_name_value ON sku_attributes(attribute_name, attribute_value);

COMMENT ON TABLE sku_attributes IS 'Flexible attribute storage for SKU variants';

-- ============================================================================
-- TRIGGERS FOR updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_skus_updated_at BEFORE UPDATE ON skus
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- SAMPLE DATA
-- ============================================================================

-- Insert categories
INSERT INTO categories (name, slug, description) VALUES
('Giày', 'giay', 'Giày dép các loại'),
('Đồng hồ', 'dong-ho', 'Đồng hồ đeo tay'),
('Laptop', 'laptop', 'Máy tính xách tay'),
('Tai nghe', 'tai-nghe', 'Tai nghe, headphone');

-- Category attributes for Giày
INSERT INTO category_attributes (category_id, name, display_name, data_type, possible_values, is_filterable) VALUES
(1, 'size', 'Kích cỡ', 'enum', '["35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45"]'::jsonb, true),
(1, 'color', 'Màu sắc', 'enum', '["Đen", "Trắng", "Xanh", "Đỏ", "Vàng", "Nâu", "Xám"]'::jsonb, true),
(1, 'gender', 'Giới tính', 'enum', '["Nam", "Nữ", "Unisex"]'::jsonb, true),
(1, 'type', 'Loại giày', 'enum', '["Thể thao", "Chạy bộ", "Sneaker", "Sandal", "Boot"]'::jsonb, true);

-- Category attributes for Đồng hồ
INSERT INTO category_attributes (category_id, name, display_name, data_type, possible_values, is_filterable) VALUES
(2, 'style', 'Phong cách', 'enum', '["Casual", "Sport", "Luxury", "Smartwatch"]'::jsonb, true),
(2, 'gender', 'Giới tính', 'enum', '["Nam", "Nữ", "Unisex"]'::jsonb, true),
(2, 'material', 'Chất liệu', 'enum', '["Da", "Kim loại", "Nhựa", "Silicon"]'::jsonb, true),
(2, 'waterproof', 'Chống nước', 'enum', '["Có", "Không"]'::jsonb, true);

-- Sample products: Nike Air Max
INSERT INTO products (category_id, title, brand, product_url, thumbnail, source) VALUES
(1, 'Nike Air Max 2024', 'Nike', 'https://tiki.vn/nike-air-max', 'nike_air_max.jpg', 'tiki');

-- Sample SKUs for Nike Air Max (different size/color combinations)
INSERT INTO skus (product_id, sku_code, price, original_price, stock) VALUES
(1, 'NIKE-AM-42-BLACK', 2500000, 3000000, 10),
(1, 'NIKE-AM-42-WHITE', 2500000, 3000000, 5),
(1, 'NIKE-AM-43-BLACK', 2500000, 3000000, 8);

-- SKU attributes
INSERT INTO sku_attributes (sku_id, attribute_name, attribute_value) VALUES
-- SKU 1: Size 42, Black
(1, 'size', '42'),
(1, 'color', 'Đen'),
(1, 'gender', 'Nam'),
(1, 'type', 'Thể thao'),
-- SKU 2: Size 42, White
(2, 'size', '42'),
(2, 'color', 'Trắng'),
(2, 'gender', 'Nam'),
(2, 'type', 'Thể thao'),
-- SKU 3: Size 43, Black
(3, 'size', '43'),
(3, 'color', 'Đen'),
(3, 'gender', 'Nam'),
(3, 'type', 'Thể thao');

-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- 1. Get all products in category "Giày" with size 42
/*
SELECT DISTINCT p.*
FROM products p
JOIN skus s ON s.product_id = p.id
JOIN sku_attributes sa ON sa.sku_id = s.id
WHERE p.category_id = 1
  AND sa.attribute_name = 'size'
  AND sa.attribute_value = '42'
  AND s.is_available = true;
*/

-- 2. Get all products with size 42 AND color Black
/*
SELECT DISTINCT p.*
FROM products p
JOIN skus s ON s.product_id = p.id
WHERE p.category_id = 1
  AND s.is_available = true
  AND EXISTS (
      SELECT 1 FROM sku_attributes sa1
      WHERE sa1.sku_id = s.id
        AND sa1.attribute_name = 'size'
        AND sa1.attribute_value = '42'
  )
  AND EXISTS (
      SELECT 1 FROM sku_attributes sa2
      WHERE sa2.sku_id = s.id
        AND sa2.attribute_name = 'color'
        AND sa2.attribute_value = 'Đen'
  );
*/

-- 3. Get available filter values for category (for UI checkboxes)
/*
SELECT 
    sa.attribute_name,
    sa.attribute_value,
    COUNT(DISTINCT s.product_id) as product_count
FROM sku_attributes sa
JOIN skus s ON s.id = sa.sku_id
JOIN products p ON p.id = s.product_id
WHERE p.category_id = 1
  AND s.is_available = true
GROUP BY sa.attribute_name, sa.attribute_value
ORDER BY sa.attribute_name, product_count DESC;
*/

-- 4. Get product with all SKUs and their attributes
/*
SELECT 
    p.id,
    p.title,
    p.brand,
    s.id as sku_id,
    s.price,
    s.stock,
    json_object_agg(sa.attribute_name, sa.attribute_value) as attributes
FROM products p
JOIN skus s ON s.product_id = p.id
LEFT JOIN sku_attributes sa ON sa.sku_id = s.id
WHERE p.id = 1
GROUP BY p.id, s.id;
*/

-- ============================================================================
-- VERIFICATION
-- ============================================================================
SELECT 'Categories' as table_name, COUNT(*) as count FROM categories
UNION ALL
SELECT 'Category Attributes', COUNT(*) FROM category_attributes
UNION ALL
SELECT 'Products', COUNT(*) FROM products
UNION ALL
SELECT 'SKUs', COUNT(*) FROM skus
UNION ALL
SELECT 'SKU Attributes', COUNT(*) FROM sku_attributes;

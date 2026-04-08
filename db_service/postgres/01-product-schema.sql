-- db_service/postgres/01-product-schema.sql
-- ProductService Database Schema
-- Database: products_db

CREATE DATABASE products_db ENCODING 'UTF8';

\c products_db

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- ============================================================================
-- PRODUCTS DATABASE SCHEMA (ProductService)
-- ============================================================================

-- Categories
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

-- Category Attributes
CREATE TABLE category_attributes (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    display_name VARCHAR(100),
    data_type VARCHAR(50) DEFAULT 'text',
    possible_values JSONB,
    is_required BOOLEAN DEFAULT FALSE,
    is_filterable BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_id, name)
);

CREATE INDEX idx_category_attributes_category ON category_attributes(category_id);
CREATE INDEX idx_category_attributes_filterable ON category_attributes(category_id, is_filterable);

-- Products
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    brand VARCHAR(100),
    description TEXT,
    product_url TEXT,
    thumbnail VARCHAR(500),
    source VARCHAR(50),  -- tiki, lazada, shopee
    tiki_product_id VARCHAR(100),
    tiki_spid VARCHAR(100),
    seller_id VARCHAR(100) DEFAULT '1',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_source ON products(source);
CREATE INDEX idx_products_active ON products(is_active);
CREATE INDEX idx_products_tiki_id ON products(tiki_product_id);

-- SKUs (Stock Keeping Units - product variants)
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

-- SKU Attributes (flexible attribute storage)
CREATE TABLE sku_attributes (
    sku_id INTEGER NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value TEXT NOT NULL,
    PRIMARY KEY (sku_id, attribute_name)
);

CREATE INDEX idx_sku_attrs_name ON sku_attributes(attribute_name);
CREATE INDEX idx_sku_attrs_value ON sku_attributes(attribute_value);
CREATE INDEX idx_sku_attrs_name_value ON sku_attributes(attribute_name, attribute_value);

-- Updated_at Triggers
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

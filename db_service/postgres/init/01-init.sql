-- ==========================================
-- DATABASE INITIALIZATION
-- ==========================================

-- Set timezone to UTC
SET timezone = 'UTC';

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- ==========================================
-- TABLES
-- ==========================================

-- Categories Table 
CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    parent_id INT REFERENCES categories(id) ON DELETE CASCADE,
    level INT DEFAULT 0 CHECK (level >= 0 AND level <= 2),
    keywords TEXT[] DEFAULT '{}',
    description TEXT,
    icon VARCHAR(50),
    priority INT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users Table
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone VARCHAR(20),
    role VARCHAR(50) DEFAULT 'user' CHECK (role IN ('user', 'admin', 'moderator')),
    is_verified BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products Table
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    slug VARCHAR(500) UNIQUE NOT NULL,
    category_id INT REFERENCES categories(id) ON DELETE SET NULL,
    brand VARCHAR(100),
    description TEXT,
    price DECIMAL(12, 2) CHECK (price >= 0),
    original_price DECIMAL(12, 2),
    discount_percent INT DEFAULT 0,
    stock INT DEFAULT 0 CHECK (stock >= 0),
    sku VARCHAR(100) UNIQUE,
    attributes JSONB DEFAULT '{}',
    images TEXT[] DEFAULT '{}',
    
    -- Metrics
    view_count INT DEFAULT 0,
    sale_count INT DEFAULT 0,
    rating_avg DECIMAL(3, 2) DEFAULT 0 CHECK (rating_avg >= 0 AND rating_avg <= 5),
    rating_count INT DEFAULT 0,
    popularity_score INT DEFAULT 0,
    
    -- Search
    search_vector tsvector,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    is_featured BOOLEAN DEFAULT false,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Search Terms Table (Mapping tìm kiếm)
CREATE TABLE search_terms (
    id SERIAL PRIMARY KEY,
    term VARCHAR(255) UNIQUE NOT NULL,
    normalized_term VARCHAR(255) NOT NULL,
    category_id INT REFERENCES categories(id) ON DELETE SET NULL,
    product_ids INT[] DEFAULT '{}',
    search_count INT DEFAULT 0,
    result_count INT DEFAULT 0,
    conversion_rate DECIMAL(5, 2) DEFAULT 0,
    last_searched TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Search History Table
CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    query VARCHAR(255) NOT NULL,
    category_id INT REFERENCES categories(id) ON DELETE SET NULL,
    result_count INT DEFAULT 0,
    clicked_product_id INT REFERENCES products(id) ON DELETE SET NULL,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100)
);

-- User Preferences Table
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    preferred_categories INT[] DEFAULT '{}',
    preferred_brands TEXT[] DEFAULT '{}',
    price_range_min DECIMAL(12, 2),
    price_range_max DECIMAL(12, 2),
    notification_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat History Table
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_user_message BOOLEAN DEFAULT true,
    product_suggestions INT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Alerts Table
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) CHECK (alert_type IN ('price_drop', 'back_in_stock', 'new_product')),
    target_price DECIMAL(12, 2),
    is_triggered BOOLEAN DEFAULT false,
    triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reviews Table
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    helpful_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Affiliate Links Table
CREATE TABLE affiliate_links (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    platform VARCHAR(100),
    affiliate_url TEXT NOT NULL,
    commission_percent DECIMAL(5, 2),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Price History Table (for tracking price changes)
CREATE TABLE price_history (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    old_price DECIMAL(12, 2),
    new_price DECIMAL(12, 2),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- INDEXES
-- ==========================================

CREATE INDEX idx_categories_slug ON categories(slug);
CREATE INDEX idx_categories_parent_id ON categories(parent_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_products_slug ON products(slug);
CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_products_sku ON products(sku);
CREATE INDEX idx_search_terms_normalized ON search_terms(normalized_term);
CREATE INDEX idx_search_history_user_id ON search_history(user_id);
CREATE INDEX idx_search_history_created_at ON search_history(searched_at);
CREATE INDEX idx_alerts_user_id ON alerts(user_id);
CREATE INDEX idx_alerts_product_id ON alerts(product_id);
CREATE INDEX idx_reviews_product_id ON reviews(product_id);
CREATE INDEX idx_reviews_user_id ON reviews(user_id);
CREATE INDEX idx_chat_history_user_id ON chat_history(user_id);
CREATE INDEX idx_price_history_product_id ON price_history(product_id);

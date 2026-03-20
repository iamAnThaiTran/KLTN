-- ============================================================================
-- SKU-BASED PRODUCT SCHEMA + USER PERSONALIZATION
-- ============================================================================

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

COMMENT ON TABLE category_attributes IS 'Attribute schema for each category';

-- ============================================================================
-- 3. PRODUCTS TABLE
-- ============================================================================
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    brand VARCHAR(100),
    description TEXT,
    product_url TEXT,
    thumbnail VARCHAR(500),
    source VARCHAR(50),
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
-- USER-RELATED TABLES (PERSONALIZATION)
-- ============================================================================

-- ============================================================================
-- 6. USERS TABLE
-- ============================================================================
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

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);

COMMENT ON TABLE users IS 'User accounts for personalization and authentication';

-- ============================================================================
-- 7. USER_PREFERENCES TABLE
-- ============================================================================
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INT UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    preferred_categories INT[] DEFAULT '{}',
    preferred_brands TEXT[] DEFAULT '{}',
    price_range_min DECIMAL(12, 2),
    price_range_max DECIMAL(12, 2),
    notification_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_preferences_user ON user_preferences(user_id);

COMMENT ON TABLE user_preferences IS 'Personalized preferences for each user';

-- ============================================================================
-- 8. SEARCH_HISTORY TABLE
-- ============================================================================
CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id) ON DELETE CASCADE,
    query VARCHAR(500) NOT NULL,
    category_id INT REFERENCES categories(id) ON DELETE SET NULL,
    category_name VARCHAR(255),
    result_count INT DEFAULT 0,
    clicked_product_id INT,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100)
);

CREATE INDEX idx_search_history_user ON search_history(user_id);
CREATE INDEX idx_search_history_category ON search_history(category_id);
CREATE INDEX idx_search_history_time ON search_history(searched_at);

COMMENT ON TABLE search_history IS 'User search history for personalization and analytics';

-- ============================================================================
-- 9. CHAT_HISTORY TABLE
-- ============================================================================
CREATE TABLE chat_history (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    is_user_message BOOLEAN DEFAULT true,
    product_suggestions INT[] DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_history_user ON chat_history(user_id);
CREATE INDEX idx_chat_history_time ON chat_history(created_at);

COMMENT ON TABLE chat_history IS 'Conversation history for assisted shopping';

-- ============================================================================
-- 10. ALERTS TABLE
-- ============================================================================
CREATE TABLE alerts (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    sku_id INT NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) CHECK (alert_type IN ('price_drop', 'back_in_stock', 'new_product')),
    target_price DECIMAL(12, 2),
    is_triggered BOOLEAN DEFAULT false,
    triggered_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_alerts_user ON alerts(user_id);
CREATE INDEX idx_alerts_sku ON alerts(sku_id);
CREATE INDEX idx_alerts_triggered ON alerts(is_triggered);

COMMENT ON TABLE alerts IS 'Price and stock alerts for users';

-- ============================================================================
-- 11. REVIEWS TABLE
-- ============================================================================
CREATE TABLE reviews (
    id SERIAL PRIMARY KEY,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating INT CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    helpful_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reviews_product ON reviews(product_id);
CREATE INDEX idx_reviews_user ON reviews(user_id);
CREATE INDEX idx_reviews_rating ON reviews(rating);

COMMENT ON TABLE reviews IS 'User reviews and ratings for products';

-- ============================================================================
-- 12. FAVORITES TABLE
-- ============================================================================
CREATE TABLE favorites (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_favorites_product ON favorites(product_id);
CREATE INDEX idx_favorites_user_added ON favorites(user_id, added_at);

COMMENT ON TABLE favorites IS 'User favorite products (wishlist)';

-- ============================================================================
-- UPDATED_AT TRIGGERS
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

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alerts_updated_at BEFORE UPDATE ON alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
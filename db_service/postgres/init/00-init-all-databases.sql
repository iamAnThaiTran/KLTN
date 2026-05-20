-- Master initialization file for all microservices databases
-- This file is executed by PostgreSQL during startup
-- It creates all 4 isolated databases with their schemas

-- ============================================================================
-- GLOBAL SETUP (Extensions and Functions)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Fuzzy text search
CREATE EXTENSION IF NOT EXISTS "unaccent";       -- Vietnamese diacritics

CREATE OR REPLACE FUNCTION unaccent_vietnamese(text)
RETURNS text AS $$
BEGIN
  RETURN unaccent($1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

SET timezone = 'Asia/Ho_Chi_Minh';

-- ============================================================================
-- DATABASE 1: PRODUCTS_DB (ProductService)
-- ============================================================================

CREATE DATABASE products_db ENCODING 'UTF8';

-- Switch to products_db and create schema
\c products_db

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE TABLE categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    slug VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    parent_category_id INTEGER,
    category_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    schema_version INTEGER DEFAULT 1,
    last_updated_attributes TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE category_attributes (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id),
    attribute_name VARCHAR(255) NOT NULL,
    attribute_type VARCHAR(50),
    is_filterable BOOLEAN DEFAULT TRUE,
    values TEXT[],
    display_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    brand VARCHAR(500),
    description TEXT,
    product_url TEXT,
    thumbnail VARCHAR(500),
    source VARCHAR(50),
    tiki_product_id VARCHAR(100),
    tiki_spid VARCHAR(100),
    seller_id VARCHAR(100) DEFAULT '1',
    is_active BOOLEAN DEFAULT TRUE,
    last_schema_version INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE skus (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    sku_code VARCHAR(100) UNIQUE,
    price DECIMAL(12, 2) NOT NULL,
    original_price DECIMAL(12, 2),
    stock INTEGER DEFAULT 0,
    is_available BOOLEAN DEFAULT TRUE,
    search_count INTEGER DEFAULT 0,
    rating DECIMAL(3, 2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sku_attributes (
    sku_id INTEGER NOT NULL REFERENCES skus(id) ON DELETE CASCADE,
    attribute_name VARCHAR(100) NOT NULL,
    attribute_value TEXT NOT NULL,
    PRIMARY KEY (sku_id, attribute_name)
);

-- Many-to-Many: Product-Category relationship for multi-category support
CREATE TABLE product_categories (
    id SERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
    is_primary BOOLEAN DEFAULT FALSE,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, category_id)
);

-- Indexes for products_db
CREATE INDEX idx_products_category ON products(category_id);
CREATE INDEX idx_products_brand ON products(brand);
CREATE INDEX idx_products_source ON products(source);
CREATE INDEX idx_products_active ON products(is_active);
CREATE INDEX idx_skus_product ON skus(product_id);
CREATE INDEX idx_skus_price ON skus(price);
CREATE INDEX idx_skus_stock ON skus(stock);
CREATE INDEX idx_skus_available ON skus(is_available);
CREATE INDEX idx_skus_search_count ON skus(search_count DESC);
CREATE INDEX idx_skus_rating ON skus(rating DESC);
CREATE INDEX idx_skus_rating_search ON skus(rating DESC, search_count DESC);

-- Indexes for product_categories (many-to-many)
CREATE INDEX idx_product_categories_product ON product_categories(product_id);
CREATE INDEX idx_product_categories_category ON product_categories(category_id);
CREATE INDEX idx_product_categories_primary ON product_categories(product_id, is_primary);

-- Timestamp trigger for products_db
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Sync product_categories when product.category_id is updated (backward compatibility)
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

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER sync_product_categories_trigger AFTER UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION sync_product_categories_on_legacy_update();

CREATE TRIGGER update_skus_updated_at BEFORE UPDATE ON skus
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Migrate existing products to product_categories (populate M2M relationship)
INSERT INTO product_categories (product_id, category_id, is_primary)
SELECT id, category_id, TRUE FROM products
WHERE category_id IS NOT NULL
ON CONFLICT DO NOTHING;

-- ============================================================================
-- DATABASE 2: RECOMMENDER_DB (RecommendatorService)
-- ============================================================================

\c postgres

CREATE DATABASE recommender_db ENCODING 'UTF8';

\c recommender_db

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE intent_cache (
    id SERIAL PRIMARY KEY,
    user_input_hash VARCHAR(64) NOT NULL UNIQUE,
    intent_type VARCHAR(50),
    confidence DECIMAL(5, 4),
    categories TEXT[],
    intent_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    hit_count INTEGER DEFAULT 0
);

CREATE TABLE ranking_weights (
    id SERIAL PRIMARY KEY,
    category_id INTEGER,
    attribute_name VARCHAR(100),
    weight DECIMAL(5, 2),
    description TEXT
);

CREATE TABLE dialogue_templates (
    id SERIAL PRIMARY KEY,
    category_id INTEGER,
    attribute_name VARCHAR(100),
    question_text TEXT NOT NULL,
    question_type VARCHAR(50),
    options JSONB,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE classification_cache (
    id SERIAL PRIMARY KEY,
    input_hash VARCHAR(64) NOT NULL UNIQUE,
    case_number INTEGER,
    case_name VARCHAR(100),
    confidence DECIMAL(5, 4),
    attributes JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE TABLE ranking_history (
    id SERIAL PRIMARY KEY,
    query_id VARCHAR(100),
    category_id INTEGER,
    ranked_products JSONB,
    user_selected_product VARCHAR(100),
    ranking_quality VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for recommender_db
CREATE INDEX idx_intent_cache_hash ON intent_cache(user_input_hash);
CREATE INDEX idx_intent_cache_expires ON intent_cache(expires_at);
CREATE INDEX idx_classification_hash ON classification_cache(input_hash);
CREATE INDEX idx_ranking_history_query ON ranking_history(query_id);
CREATE INDEX idx_ranking_history_category ON ranking_history(category_id);

-- ============================================================================
-- DATABASE 3: CRAWL_DB (CrawlService)
-- ============================================================================

\c postgres

CREATE DATABASE crawl_db ENCODING 'UTF8';

\c crawl_db

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE crawl_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(255),
    category_id INTEGER,
    attributes JSONB,
    status VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'normal',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    result JSONB
);

CREATE TABLE crawl_history (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    source VARCHAR(50),
    source_query VARCHAR(500),
    products_found INTEGER,
    products_saved INTEGER,
    crawl_duration_seconds INTEGER,
    error_occurred BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE crawl_logs (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100),
    log_level VARCHAR(20),
    message TEXT,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE crawl_statistics (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL,
    total_tasks INTEGER DEFAULT 0,
    completed_tasks INTEGER DEFAULT 0,
    failed_tasks INTEGER DEFAULT 0,
    total_products_found INTEGER DEFAULT 0,
    avg_crawl_duration_seconds DECIMAL(10, 2),
    avg_products_per_task DECIMAL(10, 2),
    sources_used TEXT[],
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(date)
);

-- Indexes for crawl_db
CREATE INDEX idx_crawl_tasks_status ON crawl_tasks(status);
CREATE INDEX idx_crawl_tasks_created ON crawl_tasks(created_at DESC);
CREATE INDEX idx_crawl_tasks_task_id ON crawl_tasks(task_id);
CREATE INDEX idx_crawl_history_task ON crawl_history(task_id);
CREATE INDEX idx_crawl_history_source ON crawl_history(source);
CREATE INDEX idx_crawl_logs_task ON crawl_logs(task_id);
CREATE INDEX idx_crawl_logs_level ON crawl_logs(log_level);
CREATE INDEX idx_crawl_stats_date ON crawl_statistics(date DESC);

-- ============================================================================
-- DATABASE 4: USER_DB (UserService)
-- ============================================================================

\c postgres

CREATE DATABASE user_db ENCODING 'UTF8';

\c user_db

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    phone VARCHAR(20),
    provider VARCHAR(50),
    provider_id VARCHAR(255),
    oauth_provider VARCHAR(50),
    oauth_id VARCHAR(255) UNIQUE,
    oauth_token VARCHAR(2000),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE REFERENCES users(user_id),
    language VARCHAR(20) DEFAULT 'en',
    preferred_currency VARCHAR(10) DEFAULT 'USD',
    price_range_min DECIMAL(10, 2),
    price_range_max DECIMAL(10, 2),
    categories TEXT[],
    brands TEXT[],
    notification_email BOOLEAN DEFAULT TRUE,
    notification_push BOOLEAN DEFAULT FALSE,
    notification_sms BOOLEAN DEFAULT FALSE,
    dark_mode BOOLEAN DEFAULT FALSE,
    comparison_limit INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    query VARCHAR(500),
    category VARCHAR(255),
    query_type VARCHAR(50),
    filters JSONB,
    results_count INTEGER,
    selected_product_id VARCHAR(100),
    clicked_at TIMESTAMP,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE favorites (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    sku_id VARCHAR(100),
    added_to_wishlist BOOLEAN DEFAULT FALSE,
    price_when_added DECIMAL(10, 2),
    current_price DECIMAL(10, 2),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, product_id)
);

CREATE TABLE price_alerts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    target_price DECIMAL(10, 2),
    current_price DECIMAL(10, 2),
    alert_type VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    triggered_count INTEGER DEFAULT 0,
    last_triggered TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_reviews (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    sku_id VARCHAR(100),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    review_images TEXT[],
    helpful_count INTEGER DEFAULT 0,
    unhelpful_count INTEGER DEFAULT 0,
    verified_purchase BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comparison_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    comparison_id VARCHAR(100) NOT NULL,
    product_ids VARCHAR(100)[],
    comparison_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    winning_product_id VARCHAR(100),
    action VARCHAR(50),
    metadata JSONB
);

-- Indexes for user_db
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_oauth ON users(oauth_provider, oauth_id);
CREATE INDEX idx_users_provider ON users(provider, provider_id);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_user_prefs_user ON user_preferences(user_id);
CREATE INDEX idx_search_history_user ON search_history(user_id);
CREATE INDEX idx_search_history_query ON search_history(query);
CREATE INDEX idx_search_history_time ON search_history(searched_at DESC);
CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_favorites_product ON favorites(product_id);
CREATE INDEX idx_price_alerts_user ON price_alerts(user_id);
CREATE INDEX idx_price_alerts_active ON price_alerts(is_active);
CREATE INDEX idx_reviews_user ON user_reviews(user_id);
CREATE INDEX idx_reviews_product ON user_reviews(product_id);
CREATE INDEX idx_reviews_rating ON user_reviews(rating);
CREATE INDEX idx_comparison_user ON comparison_history(user_id);
CREATE INDEX idx_comparison_date ON comparison_history(comparison_date DESC);

-- Timestamp triggers for user_db
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_timestamp BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_preferences_timestamp BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_reviews_timestamp BEFORE UPDATE ON user_reviews
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VERIFICATION
-- ============================================================================

\c postgres

-- List all created databases
SELECT datname FROM pg_database 
WHERE datname IN ('products_db', 'recommender_db', 'crawl_db', 'user_db')
ORDER BY datname;
 
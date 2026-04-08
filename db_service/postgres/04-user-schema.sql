-- db_service/postgres/04-user-schema.sql
-- UserService Database Schema
-- Database: user_db

CREATE DATABASE user_db ENCODING 'UTF8';

\c user_db

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- USER DATABASE SCHEMA (UserService)
-- ============================================================================

-- Users Table (Authentication and Basic Info)
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,
    username VARCHAR(255) UNIQUE,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    phone VARCHAR(20),
    provider VARCHAR(50),  -- local, google, facebook
    provider_id VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_provider ON users(provider, provider_id);
CREATE INDEX idx_users_username ON users(username);

-- User Preferences (Personalization Settings)
CREATE TABLE user_preferences (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL UNIQUE,
    language VARCHAR(20) DEFAULT 'en',
    preferred_currency VARCHAR(10) DEFAULT 'USD',
    price_range_min DECIMAL(10, 2),
    price_range_max DECIMAL(10, 2),
    categories TEXT[],  -- favorite categories
    brands TEXT[],      -- favorite brands
    notification_email BOOLEAN DEFAULT TRUE,
    notification_push BOOLEAN DEFAULT FALSE,
    notification_sms BOOLEAN DEFAULT FALSE,
    dark_mode BOOLEAN DEFAULT FALSE,
    comparison_limit INTEGER DEFAULT 5,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE INDEX idx_user_prefs_user ON user_preferences(user_id);

-- Search History (For Analytics and Recommendations)
CREATE TABLE search_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    query VARCHAR(500),
    category VARCHAR(255),
    query_type VARCHAR(50),  -- keyword, filter, comparison
    filters JSONB,  -- applied filters
    results_count INTEGER,
    selected_product_id VARCHAR(100),  -- if user clicked on result
    clicked_at TIMESTAMP,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_search_history_user ON search_history(user_id);
CREATE INDEX idx_search_history_query ON search_history(query);
CREATE INDEX idx_search_history_time ON search_history(searched_at DESC);

-- Favorites / Wishlist
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

CREATE INDEX idx_favorites_user ON favorites(user_id);
CREATE INDEX idx_favorites_product ON favorites(product_id);

-- Price Alerts (For Out-of-Stock/Price Drop Notifications)
CREATE TABLE price_alerts (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    target_price DECIMAL(10, 2),  -- alert when price drops to this
    current_price DECIMAL(10, 2),
    alert_type VARCHAR(50),  -- price_drop, stock_available, in_range
    is_active BOOLEAN DEFAULT TRUE,
    triggered_count INTEGER DEFAULT 0,
    last_triggered TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_price_alerts_user ON price_alerts(user_id);
CREATE INDEX idx_price_alerts_active ON price_alerts(is_active);

-- User Reviews and Ratings
CREATE TABLE user_reviews (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    product_id VARCHAR(100) NOT NULL,
    sku_id VARCHAR(100),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text TEXT,
    review_images TEXT[],  -- image URLs
    helpful_count INTEGER DEFAULT 0,
    unhelpful_count INTEGER DEFAULT 0,
    verified_purchase BOOLEAN DEFAULT FALSE,
    is_approved BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_reviews_user ON user_reviews(user_id);
CREATE INDEX idx_reviews_product ON user_reviews(product_id);
CREATE INDEX idx_reviews_rating ON user_reviews(rating);

-- Comparison History (For Each User's Comparisons)
CREATE TABLE comparison_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    comparison_id VARCHAR(100) NOT NULL,
    product_ids VARCHAR(100)[],
    comparison_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    winning_product_id VARCHAR(100),  -- which product user chose
    action VARCHAR(50),  -- viewed, filtered, sorted, selected
    metadata JSONB  -- additional context
);

CREATE INDEX idx_comparison_user ON comparison_history(user_id);
CREATE INDEX idx_comparison_date ON comparison_history(comparison_date DESC);

-- Auto-update timestamps
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

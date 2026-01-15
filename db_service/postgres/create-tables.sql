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
    link TEXT,
    platform VARCHAR(50),
    
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

-- Product Views Table (Tracking)
CREATE TABLE product_views (
    id SERIAL PRIMARY KEY,
    product_id INT REFERENCES products(id) ON DELETE CASCADE,
    user_id INT REFERENCES users(id) ON DELETE SET NULL,
    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_id VARCHAR(100)
);

-- Trigger để tự động update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_categories_updated_at BEFORE UPDATE ON categories
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at BEFORE UPDATE ON user_preferences
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
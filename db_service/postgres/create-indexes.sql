-- ==========================================
-- INDEXES FOR PERFORMANCE
-- ==========================================

-- Categories Indexes
CREATE INDEX idx_categories_parent ON categories(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX idx_categories_level ON categories(level, priority DESC);
CREATE INDEX idx_categories_slug ON categories(slug);
CREATE INDEX idx_categories_keywords ON categories USING GIN(keywords);
CREATE INDEX idx_categories_active ON categories(is_active) WHERE is_active = true;

-- Products Indexes
CREATE INDEX idx_products_category ON products(category_id, popularity_score DESC);
CREATE INDEX idx_products_brand ON products(brand, popularity_score DESC);
CREATE INDEX idx_products_price ON products(price);
CREATE INDEX idx_products_slug ON products(slug);
CREATE INDEX idx_products_active ON products(is_active) WHERE is_active = true;
CREATE INDEX idx_products_featured ON products(is_featured, popularity_score DESC) WHERE is_featured = true;

-- Full-text search index (Quan trọng nhất!)
CREATE INDEX idx_products_search ON products USING GIN(search_vector);

-- Trigram indexes cho fuzzy search
CREATE INDEX idx_products_name_trgm ON products USING GIN(name gin_trgm_ops);
CREATE INDEX idx_products_brand_trgm ON products USING GIN(brand gin_trgm_ops);

-- JSONB attributes index
CREATE INDEX idx_products_attributes ON products USING GIN(attributes);

-- Composite indexes
CREATE INDEX idx_products_category_price ON products(category_id, price);
CREATE INDEX idx_products_category_active ON products(category_id, is_active, popularity_score DESC);

-- Search Terms Indexes
CREATE INDEX idx_search_terms_normalized ON search_terms(normalized_term);
CREATE INDEX idx_search_terms_category ON search_terms(category_id);
CREATE INDEX idx_search_terms_count ON search_terms(search_count DESC);
CREATE INDEX idx_search_terms_last_searched ON search_terms(last_searched DESC);

-- Search History Indexes
CREATE INDEX idx_search_history_user ON search_history(user_id, searched_at DESC);
CREATE INDEX idx_search_history_query ON search_history(query, searched_at DESC);
CREATE INDEX idx_search_history_session ON search_history(session_id);

-- User Indexes
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;

-- Product Views Indexes
CREATE INDEX idx_product_views_product ON product_views(product_id, viewed_at DESC);
CREATE INDEX idx_product_views_user ON product_views(user_id, viewed_at DESC);
CREATE INDEX idx_product_views_session ON product_views(session_id);

-- Partial indexes (chỉ index data cần thiết)
CREATE INDEX idx_products_low_stock ON products(stock) WHERE stock < 10;
CREATE INDEX idx_products_on_sale ON products(discount_percent) WHERE discount_percent > 0;

COMMENT ON INDEX idx_products_search IS 'Full-text search trên tên và mô tả sản phẩm';
COMMENT ON INDEX idx_products_name_trgm IS 'Fuzzy search với trigram cho typo';
```

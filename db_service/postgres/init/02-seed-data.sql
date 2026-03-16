-- ============================================================================
-- SEED DATA - CATEGORIES
-- ============================================================================

INSERT INTO categories (name, slug, description, icon) VALUES
('Giày', 'giay', 'Giày dép các loại: thể thao, tây, sandal, dép', '👟'),
('Đồng hồ', 'dong-ho', 'Đồng hồ đeo tay, smartwatch', '⌚'),
('Laptop', 'laptop', 'Máy tính xách tay', '💻'),
('Tai nghe', 'tai-nghe', 'Tai nghe, headphone, earbuds', '🎧');

-- ============================================================================
-- SEED DATA - CATEGORY ATTRIBUTES
-- ============================================================================

-- Attributes for Giày
INSERT INTO category_attributes (category_id, name, display_name, data_type, possible_values, is_filterable, sort_order) VALUES
(1, 'size', 'Kích cỡ', 'enum', '["35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45"]'::jsonb, true, 1),
(1, 'color', 'Màu sắc', 'enum', '["Đen", "Trắng", "Xanh", "Đỏ", "Vàng", "Nâu", "Xám"]'::jsonb, true, 2),
(1, 'gender', 'Giới tính', 'enum', '["Nam", "Nữ", "Unisex"]'::jsonb, true, 3),
(1, 'type', 'Loại giày', 'enum', '["Thể thao", "Chạy bộ", "Sneaker", "Sandal", "Boot"]'::jsonb, true, 4),
(1, 'brand', 'Thương hiệu', 'text', '["Nike", "Adidas", "Puma", "Converse", "Vans"]'::jsonb, true, 5);

-- Attributes for Đồng hồ
INSERT INTO category_attributes (category_id, name, display_name, data_type, possible_values, is_filterable, sort_order) VALUES
(2, 'style', 'Phong cách', 'enum', '["Casual", "Sport", "Luxury", "Smartwatch"]'::jsonb, true, 1),
(2, 'gender', 'Giới tính', 'enum', '["Nam", "Nữ", "Unisex"]'::jsonb, true, 2),
(2, 'material', 'Chất liệu', 'enum', '["Da", "Kim loại", "Nhựa", "Silicon"]'::jsonb, true, 3),
(2, 'waterproof', 'Chống nước', 'enum', '["Có", "Không"]'::jsonb, true, 4),
(2, 'brand', 'Thương hiệu', 'text', '["Seiko", "Casio", "Citizen", "Omega"]'::jsonb, true, 5);

-- Attributes for Laptop
INSERT INTO category_attributes (category_id, name, display_name, data_type, possible_values, is_filterable, sort_order) VALUES
(3, 'brand', 'Thương hiệu', 'text', '["Apple", "Dell", "HP", "Asus", "Lenovo"]'::jsonb, true, 1),
(3, 'cpu', 'Bộ xử lý', 'text', '["Intel i5", "Intel i7", "M1", "M2", "AMD Ryzen"]'::jsonb, true, 2),
(3, 'ram', 'RAM', 'enum', '["8GB", "16GB", "32GB"]'::jsonb, true, 3),
(3, 'storage', 'Lưu trữ', 'enum', '["256GB", "512GB", "1TB"]'::jsonb, true, 4),
(3, 'screen_size', 'Kích thước màn hình', 'enum', '["13 inch", "14 inch", "15 inch", "16 inch"]'::jsonb, true, 5);

-- Attributes for Tai nghe
INSERT INTO category_attributes (category_id, name, display_name, data_type, possible_values, is_filterable, sort_order) VALUES
(4, 'type', 'Loại', 'enum', '["Over-ear", "On-ear", "In-ear", "Earbuds"]'::jsonb, true, 1),
(4, 'brand', 'Thương hiệu', 'text', '["Sony", "Bose", "Apple", "JBL", "Sennheiser"]'::jsonb, true, 2),
(4, 'noise_cancel', 'Khử tiếng ồn', 'enum', '["Có", "Không"]'::jsonb, true, 3),
(4, 'wireless', 'Wireless', 'enum', '["Có", "Không"]'::jsonb, true, 4);

-- ============================================================================
-- SEED DATA - SAMPLE PRODUCTS & SKUS
-- ============================================================================

-- Sample Product 1: Nike Air Max
INSERT INTO products (category_id, title, brand, description, product_url, thumbnail, source, is_active) VALUES
(1, 'Nike Air Max 2024', 'Nike', 'Giày thể thao Nike Air Max 2024, đế cao su Max Air', 'https://tiki.vn/nike-air-max', 'nike_air_max.jpg', 'tiki', true);

-- SKUs for Nike Air Max
INSERT INTO skus (product_id, sku_code, price, original_price, stock, is_available) VALUES
(1, 'NIKE-AM-42-BLK', 2500000.00, 3000000.00, 10, true),
(1, 'NIKE-AM-42-WHT', 2500000.00, 3000000.00, 5, true),
(1, 'NIKE-AM-43-BLK', 2500000.00, 3000000.00, 8, true);

-- SKU Attributes
INSERT INTO sku_attributes (sku_id, attribute_name, attribute_value) VALUES
(1, 'size', '42'), (1, 'color', 'Đen'), (1, 'gender', 'Nam'), (1, 'type', 'Thể thao'),
(2, 'size', '42'), (2, 'color', 'Trắng'), (2, 'gender', 'Nam'), (2, 'type', 'Thể thao'),
(3, 'size', '43'), (3, 'color', 'Đen'), (3, 'gender', 'Nam'), (3, 'type', 'Thể thao');

-- Sample Product 2: Laptop Dell XPS
INSERT INTO products (category_id, title, brand, description, product_url, thumbnail, source, is_active) VALUES
(3, 'Dell XPS 13 Plus', 'Dell', 'Laptop Dell XPS 13 Plus mỏng nhẹ, màn hình 13.3 inch OLED', 'https://lazada.vn/dell-xps', 'dell_xps.jpg', 'lazada', true);

-- SKUs for Dell XPS
INSERT INTO skus (product_id, sku_code, price, original_price, stock, is_available) VALUES
(2, 'DELL-XPS-I5-256G', 24000000.00, 30000000.00, 3, true),
(2, 'DELL-XPS-I7-512G', 32000000.00, 40000000.00, 2, true);

-- SKU Attributes
INSERT INTO sku_attributes (sku_id, attribute_name, attribute_value) VALUES
(4, 'brand', 'Dell'), (4, 'cpu', 'Intel i5'), (4, 'ram', '16GB'), (4, 'storage', '256GB'), (4, 'screen_size', '13 inch'),
(5, 'brand', 'Dell'), (5, 'cpu', 'Intel i7'), (5, 'ram', '16GB'), (5, 'storage', '512GB'), (5, 'screen_size', '13 inch');

-- Sample Product 3: Smartwatch
INSERT INTO products (category_id, title, brand, description, product_url, thumbnail, source, is_active) VALUES
(2, 'Apple Watch Series 9', 'Apple', 'Smartwatch Apple Watch Series 9, 45mm', 'https://shopee.vn/apple-watch', 'apple_watch.jpg', 'shopee', true);

-- SKUs for Apple Watch
INSERT INTO skus (product_id, sku_code, price, original_price, stock, is_available) VALUES
(3, 'APPLE-WATCH-BLK-45', 11000000.00, 13000000.00, 5, true),
(3, 'APPLE-WATCH-SLV-45', 11000000.00, 13000000.00, 4, true);

-- SKU Attributes
INSERT INTO sku_attributes (sku_id, attribute_name, attribute_value) VALUES
(6, 'brand', 'Apple'), (6, 'style', 'Smartwatch'), (6, 'waterproof', 'Có'),
(7, 'brand', 'Apple'), (7, 'style', 'Smartwatch'), (7, 'waterproof', 'Có');

-- ============================================================================
-- SEED DATA - USERS
-- ============================================================================

-- Create admin user (password: admin123)
INSERT INTO users (email, password_hash, full_name, role, is_verified, is_active) VALUES
('admin@kltn.com', '$2b$10$3vFzpM7RxF0Y0YR7DqM5beLj7zL7P8Nz4K6Q2M9V1X5Z2W3A4B5C6', 'Admin User', 'admin', true, true);

-- Create demo users
INSERT INTO users (email, password_hash, full_name, role, is_verified, is_active) VALUES
('demo@example.com', '$2b$10$5sL6P9D2Q1R8E7T4Y3K0vOM5N1B9V7Z4X2C6M8W1A3F5S7D9E0K1', 'Demo User', 'user', true, true),
('user1@example.com', '$2b$10$7tN1M8K3Q4R5S6T7U8V9W0X1Y2Z3A4B5C6D7E8F9G0H1I2J3K4L5M', 'Nguyễn Văn A', 'user', true, true);

-- ============================================================================
-- SEED DATA - USER PREFERENCES
-- ============================================================================

-- Admin preferences
INSERT INTO user_preferences (user_id, preferred_categories, preferred_brands, price_range_min, price_range_max, notification_enabled) VALUES
(1, ARRAY[1, 2, 3], ARRAY['Nike', 'Apple', 'Dell'], 1000000.00, 50000000.00, true);

-- Demo user preferences
INSERT INTO user_preferences (user_id, preferred_categories, preferred_brands, price_range_min, price_range_max, notification_enabled) VALUES
(2, ARRAY[1, 4], ARRAY['Nike', 'Sony', 'JBL'], 500000.00, 10000000.00, true);

-- User1 preferences
INSERT INTO user_preferences (user_id, preferred_categories, preferred_brands, price_range_min, price_range_max, notification_enabled) VALUES
(3, ARRAY[3], ARRAY['Apple', 'Dell', 'HP'], 20000000.00, 50000000.00, true);

-- ============================================================================
-- SEED DATA - SAMPLE ALERTS
-- ============================================================================

-- Alert: Price drop for Nike Air Max Size 42 Black
INSERT INTO alerts (user_id, sku_id, alert_type, target_price, is_triggered) VALUES
(2, 1, 'price_drop', 2200000.00, false);

-- Alert: Back in stock for Dell XPS
INSERT INTO alerts (user_id, sku_id, alert_type, is_triggered) VALUES
(3, 4, 'back_in_stock', false);

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
SELECT 'SKU Attributes', COUNT(*) FROM sku_attributes
UNION ALL
SELECT 'Users', COUNT(*) FROM users
UNION ALL
SELECT 'User Preferences', COUNT(*) FROM user_preferences
UNION ALL
SELECT 'Alerts', COUNT(*) FROM alerts;

-- Insert Sample Products
INSERT INTO products (name, slug, category_id, brand, description, price, original_price, discount_percent, stock, sku, attributes, popularity_score, is_featured) VALUES
-- iPhones
('iPhone 15 Pro Max 256GB', 'iphone-15-pro-max-256gb', 12, 'Apple', 'iPhone 15 Pro Max với chip A17 Pro, camera 48MP', 34990000, 36990000, 5, 50, 'IP15PM256', 
 '{"màu": ["Titan Tự Nhiên", "Titan Xanh", "Titan Trắng", "Titan Đen"], "bộ nhớ": "256GB", "ram": "8GB"}'::jsonb, 9500, true),

('iPhone 15 Plus 128GB', 'iphone-15-plus-128gb', 12, 'Apple', 'iPhone 15 Plus màn hình lớn 6.7 inch', 25990000, 27990000, 7, 80, 'IP15P128',
 '{"màu": ["Hồng", "Vàng", "Xanh", "Đen"], "bộ nhớ": "128GB", "ram": "6GB"}'::jsonb, 8800, true),

('iPhone 14 128GB', 'iphone-14-128gb', 12, 'Apple', 'iPhone 14 chip A15 Bionic', 19990000, 22990000, 13, 120, 'IP14128',
 '{"màu": ["Tím", "Xanh", "Đỏ", "Trắng"], "bộ nhớ": "128GB", "ram": "6GB"}'::jsonb, 8500, false),

-- Samsung
('Samsung Galaxy S24 Ultra 256GB', 'samsung-galaxy-s24-ultra-256gb', 13, 'Samsung', 'Galaxy S24 Ultra với S Pen, camera 200MP', 31990000, 33990000, 6, 60, 'SGS24U256',
 '{"màu": ["Titan Xám", "Titan Đen", "Titan Tím"], "bộ nhớ": "256GB", "ram": "12GB"}'::jsonb, 9200, true),

('Samsung Galaxy A54 5G 128GB', 'samsung-galaxy-a54-5g-128gb', 13, 'Samsung', 'Galaxy A54 5G giá tầm trung', 10490000, 11990000, 13, 150, 'SGA54128',
 '{"màu": ["Xanh", "Tím", "Đen"], "bộ nhớ": "128GB", "ram": "8GB"}'::jsonb, 7800, false),

-- Xiaomi
('Xiaomi 14 Pro 512GB', 'xiaomi-14-pro-512gb', 14, 'Xiaomi', 'Xiaomi 14 Pro Snapdragon 8 Gen 3', 24990000, 26990000, 7, 40, 'XM14P512',
 '{"màu": ["Đen", "Trắng"], "bộ nhớ": "512GB", "ram": "16GB"}'::jsonb, 7500, true),

-- Laptops
('MacBook Air M3 13 inch 256GB', 'macbook-air-m3-13-256gb', 15, 'Apple', 'MacBook Air M3 mỏng nhẹ', 28990000, 30990000, 6, 30, 'MBAM3256',
 '{"màu": ["Xám", "Vàng", "Bạc"], "chip": "M3", "ram": "8GB", "ssd": "256GB"}'::jsonb, 9000, true),

('Dell XPS 13 Plus i7', 'dell-xps-13-plus-i7', 16, 'Dell', 'Dell XPS 13 Plus Intel Core i7 gen 13', 42990000, 45990000, 7, 20, 'DXPS13I7',
 '{"màu": ["Bạc", "Đen"], "cpu": "i7-1360P", "ram": "16GB", "ssd": "512GB"}'::jsonb, 7200, false),

('Asus Vivobook 15 OLED', 'asus-vivobook-15-oled', 17, 'Asus', 'Asus Vivobook 15 màn hình OLED', 15990000, 17990000, 11, 70, 'ASVB15O',
 '{"màu": ["Bạc", "Xanh"], "cpu": "i5-12500H", "ram": "8GB", "ssd": "512GB"}'::jsonb, 6800, false),

-- Bột giặt
('Omo Matic Comfort 3.8kg', 'omo-matic-comfort-3-8kg', 18, 'Omo', 'Bột giặt Omo Matic cho máy giặt cửa trước', 189000, 219000, 14, 500, 'OMOMC38',
 '{"khối lượng": "3.8kg", "loại": "Máy giặt", "hương": "Comfort"}'::jsonb, 8500, true),

('Omo Đỏ 6kg', 'omo-do-6kg', 18, 'Omo', 'Bột giặt Omo đỏ truyền thống', 149000, 169000, 12, 800, 'OMOD6',
 '{"khối lượng": "6kg", "loại": "Giặt tay", "hương": "Truyền thống"}'::jsonb, 8200, false),

('Tide Trắng Sáng 3.8kg', 'tide-trang-sang-3-8kg', 19, 'Tide', 'Bột giặt Tide giữ trắng quần áo', 199000, 229000, 13, 400, 'TIDETS38',
 '{"khối lượng": "3.8kg", "loại": "Máy giặt", "công dụng": "Trắng sáng"}'::jsonb, 7900, false);

-- Insert Search Terms (Pre-populate common searches)
INSERT INTO search_terms (term, normalized_term, category_id, search_count) VALUES
('điện thoại', 'dien thoai', 5, 15000),
('iphone', 'iphone', 12, 12000),
('laptop', 'laptop', 6, 8000),
('bột giặt', 'bot giat', 9, 6500),
('samsung', 'samsung', 13, 5800),
('macbook', 'macbook', 15, 4200),
('tai nghe', 'tai nghe', 7, 3800),
('iphone 15', 'iphone 15', 12, 3500),
('xiaomi', 'xiaomi', 14, 2900),
('omo', 'omo', 18, 2500);

ANALYZE;

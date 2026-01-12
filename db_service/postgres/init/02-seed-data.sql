-- ==========================================
-- SEED DATA
-- ==========================================

-- Insert Categories (Level 0 - Root)
INSERT INTO categories (name, slug, level, keywords, icon, priority) VALUES
('Điện tử', 'dien-tu', 0, ARRAY['điện tử', 'electronics', 'công nghệ'], '💻', 100),
('Gia dụng', 'gia-dung', 0, ARRAY['gia dụng', 'household', 'nhà cửa'], '🏠', 90),
('Thời trang', 'thoi-trang', 0, ARRAY['thời trang', 'fashion', 'quần áo'], '👗', 80),
('Sách', 'sach', 0, ARRAY['sách', 'books', 'đọc'], '📚', 70);

-- Insert Categories (Level 1 - Sub categories)
INSERT INTO categories (name, slug, parent_id, level, keywords, icon, priority) VALUES
-- Điện tử
('Điện thoại', 'dien-thoai', 1, 1, ARRAY['điện thoại', 'smartphone', 'di động', 'phone'], '📱', 100),
('Laptop', 'laptop', 1, 1, ARRAY['laptop', 'máy tính xách tay', 'notebook'], '💻', 90),
('Tai nghe', 'tai-nghe', 1, 1, ARRAY['tai nghe', 'headphone', 'earphone'], '🎧', 80),
('Máy tính bảng', 'may-tinh-bang', 1, 1, ARRAY['máy tính bảng', 'tablet', 'ipad'], '📲', 70),

-- Gia dụng
('Bột giặt', 'bot-giat', 2, 1, ARRAY['bột giặt', 'nước giặt', 'detergent'], '🧼', 100),
('Nước rửa chén', 'nuoc-rua-chen', 2, 1, ARRAY['nước rửa chén', 'dishwashing', 'rửa bát'], '🧽', 90),
('Dụng cụ nhà bếp', 'dung-cu-nha-bep', 2, 1, ARRAY['dụng cụ nhà bếp', 'kitchen', 'nấu ăn'], '🍳', 80);

-- Insert Categories (Level 2 - Brands/Specific)
INSERT INTO categories (name, slug, parent_id, level, keywords, priority) VALUES
-- Điện thoại brands
('iPhone', 'iphone', 5, 2, ARRAY['iphone', 'apple', 'ios'], 100),
('Samsung', 'samsung', 5, 2, ARRAY['samsung', 'galaxy'], 90),
('Xiaomi', 'xiaomi', 5, 2, ARRAY['xiaomi', 'redmi', 'poco'], 80),

-- Laptop brands
('MacBook', 'macbook', 6, 2, ARRAY['macbook', 'apple', 'mac'], 100),
('Dell', 'dell', 6, 2, ARRAY['dell', 'latitude', 'xps'], 90),
('Asus', 'asus', 6, 2, ARRAY['asus', 'vivobook', 'zenbook'], 80),

-- Bột giặt brands
('Omo', 'omo', 9, 2, ARRAY['omo', 'unilever'], 100),
('Tide', 'tide', 9, 2, ARRAY['tide', 'p&g'], 90);

-- Create admin user (password: admin123)
-- Hash was generated with: bcrypt.hash('admin123', 10)
INSERT INTO users (email, password_hash, full_name, role, is_verified, is_active) VALUES
('admin@kltn.com', '$2b$10$3vFzpM7RxF0Y0YR7DqM5beLj7zL7P8Nz4K6Q2M9V1X5Z2W3A4B5C6', 'Admin User', 'admin', true, true);

-- Create demo user (password: demo123)
-- Hash was generated with: bcrypt.hash('demo123', 10)
INSERT INTO users (email, password_hash, full_name, role, is_verified, is_active) VALUES
('demo@example.com', '$2b$10$5sL6P9D2Q1R8E7T4Y3K0vOM5N1B9V7Z4X2C6M8W1A3F5S7D9E0K1', 'Demo User', 'user', true, true);

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

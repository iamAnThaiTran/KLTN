-- Khởi tạo database và extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Fuzzy text search
CREATE EXTENSION IF NOT EXISTS "unaccent"; -- Loại bỏ dấu tiếng Việt

-- Function để normalize tiếng Việt
CREATE OR REPLACE FUNCTION unaccent_vietnamese(text)
RETURNS text AS $$
BEGIN
  RETURN unaccent($1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Set timezone
SET timezone = 'Asia/Ho_Chi_Minh';

-- Comment
COMMENT ON DATABASE product_db IS 'Product search and recommendation database';
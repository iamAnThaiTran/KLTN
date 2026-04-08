-- db_service/postgres/init-all-databases.sql
-- Master initialization script for all microservice databases
-- This script initializes PostgreSQL for the true microservices architecture

-- ============================================================================
-- GLOBAL SETUP
-- ============================================================================

-- Create extensions at global level
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Fuzzy text search
CREATE EXTENSION IF NOT EXISTS "unaccent";       -- Vietnamese diacritics

-- Function to normalize Vietnamese text
CREATE OR REPLACE FUNCTION unaccent_vietnamese(text)
RETURNS text AS $$
BEGIN
  RETURN unaccent($1);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Set timezone
SET timezone = 'Asia/Ho_Chi_Minh';

-- ============================================================================
-- DATABASE 1: Products Database (ProductService)
-- ============================================================================

\i /docker-entrypoint-initdb.d/01-product-schema.sql

-- ============================================================================
-- DATABASE 2: Recommender Database (RecommendatorService)
-- ============================================================================

\i /docker-entrypoint-initdb.d/02-recommender-schema.sql

-- ============================================================================
-- DATABASE 3: Crawl Database (CrawlService)
-- ============================================================================

\i /docker-entrypoint-initdb.d/03-crawl-schema.sql

-- ============================================================================
-- DATABASE 4: User Database (UserService)
-- ============================================================================

\i /docker-entrypoint-initdb.d/04-user-schema.sql

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Verify all databases are created
\connect postgres

SELECT datname FROM pg_database 
WHERE datname IN ('products_db', 'recommender_db', 'crawl_db', 'user_db');

-- Output: List of all created databases for verification

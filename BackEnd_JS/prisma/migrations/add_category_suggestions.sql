-- Migration: Add category suggestions and dynamic schema tables
-- Created: 2026-01-28

-- Table: category_suggestions
-- Stores LLM-suggested categories with metadata
CREATE TABLE IF NOT EXISTS category_suggestions (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(255) UNIQUE NOT NULL,
    confidence DECIMAL(3, 2) DEFAULT 0.00,
    reason TEXT,
    attributes JSONB DEFAULT '[]',
    keywords TEXT[] DEFAULT '{}',
    source VARCHAR(50) DEFAULT 'llm',
    usage_count INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_category_suggestions_name_active 
    ON category_suggestions(category_name, is_active);

CREATE INDEX idx_category_suggestions_usage 
    ON category_suggestions(usage_count DESC);

-- Table: dynamic_category_schemas
-- Stores generated schemas for dynamic categories
CREATE TABLE IF NOT EXISTS dynamic_category_schemas (
    id SERIAL PRIMARY KEY,
    category_name VARCHAR(255) NOT NULL,
    schema_json JSONB NOT NULL,
    suggestion_id INTEGER REFERENCES category_suggestions(id) ON DELETE SET NULL,
    generated_by VARCHAR(50) DEFAULT 'llm',
    version INTEGER DEFAULT 1,
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(5, 2) DEFAULT 0.00,
    is_active BOOLEAN DEFAULT true,
    is_verified BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(category_name, version)
);

CREATE INDEX idx_dynamic_schemas_name_active 
    ON dynamic_category_schemas(category_name, is_active);

CREATE INDEX idx_dynamic_schemas_version 
    ON dynamic_category_schemas(category_name, version DESC);

-- Trigger: Update updated_at on modification
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_category_suggestions_updated_at 
    BEFORE UPDATE ON category_suggestions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_dynamic_schemas_updated_at 
    BEFORE UPDATE ON dynamic_category_schemas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE category_suggestions IS 'LLM-suggested product categories with attributes';
COMMENT ON TABLE dynamic_category_schemas IS 'Generated schemas for dynamic product categories';
COMMENT ON COLUMN category_suggestions.confidence IS 'LLM confidence score (0.00-1.00)';
COMMENT ON COLUMN dynamic_category_schemas.success_rate IS 'Success rate of schema usage (0.00-100.00)';

-- db_service/postgres/02-recommender-schema.sql
-- RecommendatorService Database Schema
-- Database: recommender_db

CREATE DATABASE recommender_db ENCODING 'UTF8';

\c recommender_db

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- RECOMMENDER DATABASE SCHEMA (RecommendatorService)
-- ============================================================================

-- Intent Cache (cache for detected intents to avoid re-computing)
CREATE TABLE intent_cache (
    id SERIAL PRIMARY KEY,
    user_input_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA256 hash of user input
    intent_type VARCHAR(50),  -- specific, abstract, comparison, none
    confidence DECIMAL(5, 4),
    categories TEXT[],
    product_name VARCHAR(255),
    intent_data JSONB,  -- full intent details
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,  -- for cleanup
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX idx_intent_cache_expires ON intent_cache(expires_at);
CREATE INDEX idx_intent_cache_hit ON intent_cache(hit_count DESC);

-- Ranking Configuration (weights for product ranking)
CREATE TABLE ranking_weights (
    id SERIAL PRIMARY KEY,
    category_id INTEGER,
    attribute_name VARCHAR(100),
    weight DECIMAL(5, 2),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_ranking_weights_category_attr 
    ON ranking_weights(category_id, attribute_name);

-- Dialogue Templates (for question generation)
CREATE TABLE dialogue_templates (
    id SERIAL PRIMARY KEY,
    category_id INTEGER,
    attribute_name VARCHAR(100),
    question_text TEXT NOT NULL,
    question_type VARCHAR(50),  -- yes_no, multiple_choice, text
    options JSONB,  -- for multiple choice
    display_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_dialogue_category ON dialogue_templates(category_id);
CREATE INDEX idx_dialogue_attribute ON dialogue_templates(attribute_name);

-- Request Classification Cache (cache for 7-case classification)
CREATE TABLE classification_cache (
    id SERIAL PRIMARY KEY,
    conversation_hash VARCHAR(64) NOT NULL UNIQUE,
    case_number INTEGER,
    case_name VARCHAR(100),
    action VARCHAR(50),
    confidence DECIMAL(5, 4),
    classification_data JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP
);

CREATE INDEX idx_classification_expires ON classification_cache(expires_at);

-- Ranking History (for analysis and improvement)
CREATE TABLE ranking_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    category VARCHAR(255),
    query VARCHAR(500),
    ranked_products JSONB,  -- [{id, score, rank}, ...]
    user_clicked_product_id INTEGER,
    session_id VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_ranking_user ON ranking_history(user_id);
CREATE INDEX idx_ranking_category ON ranking_history(category);
CREATE INDEX idx_ranking_session ON ranking_history(session_id);

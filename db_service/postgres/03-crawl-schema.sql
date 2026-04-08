-- db_service/postgres/03-crawl-schema.sql
-- CrawlService Database Schema
-- Database: crawl_db

CREATE DATABASE crawl_db ENCODING 'UTF8';

\c crawl_db

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CRAWL DATABASE SCHEMA (CrawlService)
-- ============================================================================

-- Crawl Tasks (for RabbitMQ task tracking)
CREATE TABLE crawl_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL UNIQUE,  -- crawl_abc123
    category VARCHAR(255),
    category_id INTEGER,
    attributes JSONB,
    status VARCHAR(50),  -- pending, running, completed, failed, cancelled
    priority VARCHAR(20) DEFAULT 'normal',  -- high, normal, low
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    result JSONB  -- {products_found, sources, ...}
);

CREATE INDEX idx_crawl_tasks_status ON crawl_tasks(status);
CREATE INDEX idx_crawl_tasks_created ON crawl_tasks(created_at DESC);
CREATE INDEX idx_crawl_tasks_task_id ON crawl_tasks(task_id);

-- Crawl History (detailed logs of each crawl operation)
CREATE TABLE crawl_history (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100) NOT NULL,
    source VARCHAR(50),  -- tiki, lazada, shopee
    source_query VARCHAR(500),
    products_found INTEGER,
    products_saved INTEGER,
    crawl_duration_seconds INTEGER,
    error_occurred BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES crawl_tasks(task_id) ON DELETE CASCADE
);

CREATE INDEX idx_crawl_history_task ON crawl_history(task_id);
CREATE INDEX idx_crawl_history_source ON crawl_history(source);
CREATE INDEX idx_crawl_history_created ON crawl_history(started_at DESC);

-- Crawl Logs (for debugging and monitoring)
CREATE TABLE crawl_logs (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(100),
    log_level VARCHAR(20),  -- INFO, WARNING, ERROR
    message TEXT,
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_crawl_logs_task ON crawl_logs(task_id);
CREATE INDEX idx_crawl_logs_level ON crawl_logs(log_level);
CREATE INDEX idx_crawl_logs_created ON crawl_logs(created_at DESC);

-- Crawl Statistics (for monitoring and optimization)
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

CREATE INDEX idx_crawl_stats_date ON crawl_statistics(date DESC);

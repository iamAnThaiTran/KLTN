-- ============================================================================
-- COMPARISON HISTORY TABLE
-- ============================================================================

CREATE TABLE comparison_history (
    id SERIAL PRIMARY KEY,
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Product IDs being compared (stored as product IDs in our DB)
    product_id_1 INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    product_id_2 INT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    
    -- Product titles for quick display
    product_name_1 VARCHAR(500),
    product_name_2 VARCHAR(500),
    
    -- Comparison metadata
    comparison_type VARCHAR(50) DEFAULT 'detailed',  -- 'detailed', 'quick', 'vs'
    llm_model VARCHAR(100) DEFAULT 'gpt-4',  -- which LLM was used
    
    -- Full comparison result (stored as JSON for flexibility)
    snapshot_a JSONB,  -- Full product snapshot A
    snapshot_b JSONB,  -- Full product snapshot B
    comparison_result TEXT,  -- Markdown comparison text
    summary_json JSONB,  -- Summary data (best for comfort, price, etc.)
    
    -- Original API request for reproducibility
    api_request JSONB,
    
    -- Metadata
    notes VARCHAR(500),  -- User notes about the comparison
    is_starred BOOLEAN DEFAULT false,  -- User can star favorites
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for fast queries
CREATE INDEX idx_comparison_history_user ON comparison_history(user_id);
CREATE INDEX idx_comparison_history_created ON comparison_history(user_id, created_at DESC);
CREATE INDEX idx_comparison_history_products ON comparison_history(product_id_1, product_id_2);
CREATE INDEX idx_comparison_history_starred ON comparison_history(user_id, is_starred);

COMMENT ON TABLE comparison_history IS 'Stores product comparison history for each user';
COMMENT ON COLUMN comparison_history.snapshot_a IS 'Full product data snapshot from API';
COMMENT ON COLUMN comparison_history.snapshot_b IS 'Full product data snapshot from API';
COMMENT ON COLUMN comparison_history.comparison_result IS 'Markdown formatted comparison from LLM';
COMMENT ON COLUMN comparison_history.summary_json IS 'Structured summary (best for comfort, price, overall)';
COMMENT ON COLUMN comparison_history.api_request IS 'Original request data for reproducibility';

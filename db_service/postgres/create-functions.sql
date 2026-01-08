-- Function: Update search_vector khi insert/update product
CREATE OR REPLACE FUNCTION update_product_search_vector()
RETURNS TRIGGER AS $
BEGIN
    NEW.search_vector := 
        setweight(to_tsvector('simple', unaccent(COALESCE(NEW.name, ''))), 'A') ||
        setweight(to_tsvector('simple', unaccent(COALESCE(NEW.brand, ''))), 'B') ||
        setweight(to_tsvector('simple', unaccent(COALESCE(NEW.description, ''))), 'C');
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_product_search_vector
    BEFORE INSERT OR UPDATE ON products
    FOR EACH ROW
    EXECUTE FUNCTION update_product_search_vector();

-- Function: Update popularity_score
CREATE OR REPLACE FUNCTION calculate_popularity_score(
    p_view_count INT,
    p_sale_count INT,
    p_rating_avg DECIMAL,
    p_rating_count INT
) RETURNS INT AS $
BEGIN
    RETURN (
        (p_view_count * 1) +
        (p_sale_count * 10) +
        (p_rating_avg * p_rating_count * 5)
    )::INT;
END;
$ LANGUAGE plpgsql IMMUTABLE;

-- Function: Get product suggestions (Smart search)
CREATE OR REPLACE FUNCTION get_product_suggestions(
    search_query TEXT,
    limit_count INT DEFAULT 10
)
RETURNS TABLE (
    id INT,
    name VARCHAR(500),
    brand VARCHAR(100),
    price DECIMAL(12,2),
    category_name VARCHAR(255),
    rank REAL
) AS $
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.name,
        p.brand,
        p.price,
        c.name as category_name,
        ts_rank(p.search_vector, plainto_tsquery('simple', unaccent(search_query))) as rank
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE 
        p.is_active = true
        AND (
            p.search_vector @@ plainto_tsquery('simple', unaccent(search_query))
            OR p.name ILIKE '%' || search_query || '%'
            OR p.brand ILIKE '%' || search_query || '%'
        )
    ORDER BY 
        rank DESC,
        p.popularity_score DESC
    LIMIT limit_count;
END;
$ LANGUAGE plpgsql;

-- Function: Get trending searches
CREATE OR REPLACE FUNCTION get_trending_searches(limit_count INT DEFAULT 10)
RETURNS TABLE (
    term VARCHAR(255),
    search_count INT,
    category_name VARCHAR(255)
) AS $
BEGIN
    RETURN QUERY
    SELECT 
        st.term,
        st.search_count,
        c.name as category_name
    FROM search_terms st
    LEFT JOIN categories c ON st.category_id = c.id
    WHERE st.last_searched > NOW() - INTERVAL '7 days'
    ORDER BY st.search_count DESC
    LIMIT limit_count;
END;
$ LANGUAGE plpgsql;

-- Function: Track product view
CREATE OR REPLACE FUNCTION track_product_view(
    p_product_id INT,
    p_user_id INT DEFAULT NULL,
    p_session_id VARCHAR(100) DEFAULT NULL
) RETURNS VOID AS $
BEGIN
    -- Insert view record
    INSERT INTO product_views (product_id, user_id, session_id)
    VALUES (p_product_id, p_user_id, p_session_id);
    
    -- Update product view count
    UPDATE products 
    SET view_count = view_count + 1,
        popularity_score = calculate_popularity_score(
            view_count + 1,
            sale_count,
            rating_avg,
            rating_count
        )
    WHERE id = p_product_id;
END;
$ LANGUAGE plpgsql;

-- Function: Get category hierarchy
CREATE OR REPLACE FUNCTION get_category_path(category_id INT)
RETURNS TEXT AS $
DECLARE
    path TEXT := '';
    current_id INT := category_id;
    current_name VARCHAR(255);
    parent_id INT;
BEGIN
    LOOP
        SELECT name, c.parent_id INTO current_name, parent_id
        FROM categories c
        WHERE c.id = current_id;
        
        EXIT WHEN current_id IS NULL;
        
        IF path = '' THEN
            path := current_name;
        ELSE
            path := current_name || ' > ' || path;
        END IF;
        
        current_id := parent_id;
    END LOOP;
    
    RETURN path;
END;
$ LANGUAGE plpgsql;

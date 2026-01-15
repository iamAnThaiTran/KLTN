import { logger } from '../utils/logger.js';
import { pool } from '../config/database.js';
import { crawlerService } from './crawler.service.js';

/**
 * Product Service
 * Xử lý search và filter products từ database
 * Fallback to crawlers nếu không có data trong database
 */
class ProductService {
  /**
   * Search products từ database, crawl if needed
   * @param {string} searchQuery - Search query đã được extract từ intent
   * @param {object} filters - Structured filters (price, category, brand...)
   * @returns {Promise<Array>} - Danh sách products
   */
  async searchProducts(searchQuery, filters = {}) {
    try {
      logger.info(`[ProductService] Searching: "${searchQuery}"`);
      logger.info(`[ProductService] Filters:`, filters);

      // Step 1: Try to search in database first
      let results = await this.searchDatabase(searchQuery, filters);
      
      // Step 2: If no results in DB and force_refresh or not enough results, crawl from platforms
      if ((!results || results.length === 0) || (filters.forceRefresh && results.length < 20)) {
        logger.info(`[ProductService] Database returned ${results?.length || 0} results. Crawling platforms...`);
        
        const crawledProducts = await crawlerService.crawlAll(searchQuery);
        
        if (crawledProducts.length > 0) {
          // Save crawled products to database
          await this.saveProductsToDB(crawledProducts, searchQuery);
          results = crawledProducts;
        }
      }
      
      // Step 3: Rank results
      const rankedProducts = this.rankProducts(results || [], searchQuery, filters);
      
      logger.info(`[ProductService] Found ${rankedProducts.length} products`);
      
      return rankedProducts;

    } catch (error) {
      logger.error('[ProductService] Search error:', error);
      throw error;
    }
  }

  /**
   * Search products in database
   * @private
   */
  async searchDatabase(searchQuery, filters) {
    try {
      // Build SQL query
      let sql = `
        SELECT 
          id, name, slug, category_id, brand, description, price, original_price, 
          discount_percent, stock, images, rating_avg, rating_count, popularity_score
        FROM products 
        WHERE is_active = true
      `;
      
      const params = [];
      let paramCount = 1;

      // Text search using full text search or LIKE
      sql += ` AND (
        name ILIKE $${paramCount} 
        OR description ILIKE $${paramCount}
        OR brand ILIKE $${paramCount}
      )`;
      params.push(`%${searchQuery}%`);
      paramCount++;

      // Price range filter
      if (filters.price_min !== undefined) {
        sql += ` AND price >= $${paramCount}`;
        params.push(filters.price_min);
        paramCount++;
      }

      if (filters.price_max !== undefined) {
        sql += ` AND price <= $${paramCount}`;
        params.push(filters.price_max);
        paramCount++;
      }

      // Category filter
      if (filters.category) {
        sql += ` AND category_id = $${paramCount}`;
        params.push(filters.category);
        paramCount++;
      }

      // Brand filter
      if (filters.brand) {
        sql += ` AND LOWER(brand) = LOWER($${paramCount})`;
        params.push(filters.brand);
        paramCount++;
      }

      // Order and limit
      sql += ` ORDER BY popularity_score DESC, rating_avg DESC LIMIT 100`;

      const result = await pool.query(sql, params);
      
      return result.rows.map(row => ({
        id: row.id,
        title: row.name,
        name: row.name,
        slug: row.slug,
        category_id: row.category_id,
        brand: row.brand,
        description: row.description,
        price: parseFloat(row.price),
        original_price: parseFloat(row.original_price),
        discount_percent: row.discount_percent,
        stock: row.stock,
        images: row.images,
        rating: row.rating_avg,
        rating_avg: row.rating_avg,
        rating_count: row.rating_count,
        popularity_score: row.popularity_score,
        source: 'database'
      }));
    } catch (error) {
      logger.error('[ProductService] Database search error:', error);
      return [];
    }
  }

  /**
   * Save crawled products to database
   * @private
   */
  async saveProductsToDB(products, searchQuery) {
    try {
      logger.info(`[ProductService] Saving ${products.length} products to database`);
      
      for (const product of products) {
        try {
          const slug = product.title?.toLowerCase().replace(/\s+/g, '-') || 'product';
          
          const sql = `
            INSERT INTO products (name, slug, brand, price, original_price, discount_percent, images, rating_avg, rating_count, link, platform, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, true)
            ON CONFLICT (slug) DO UPDATE SET 
              price = $4,
              original_price = $5,
              discount_percent = $6,
              rating_avg = $8,
              rating_count = $9,
              link = $10,
              platform = $11,
              updated_at = CURRENT_TIMESTAMP
            RETURNING id;
          `;
          
          const values = [
            product.title,
            slug,
            product.brand || 'Unknown',
            product.price || 0,
            product.priceOriginal || product.price || 0,
            product.discount || 0,
            product.image ? [product.image] : [],
            product.rating || 0,
            product.reviews || 0,
            product.link || '',
            product.platform || product.source || 'unknown'
          ];
          
          await pool.query(sql, values);
        } catch (error) {
          logger.warn(`[ProductService] Failed to save product ${product.title}:`, error.message);
          // Continue with next product
        }
      }
      
      logger.info(`[ProductService] Completed saving products`);
    } catch (error) {
      logger.error('[ProductService] Error saving products to DB:', error);
    }
  }

  /**
   * Rank products based on relevance
   * Simple scoring algorithm
   */
  rankProducts(products, searchQuery, filters) {
    return products.map(product => {
      let score = 0;

      // Text relevance score
      const queryTerms = searchQuery.toLowerCase().split(' ');
      const titleLower = (product.title || product.name || '').toLowerCase();
      const descLower = (product.description || '').toLowerCase();

      queryTerms.forEach(term => {
        if (titleLower.includes(term)) score += 10;
        if (descLower.includes(term)) score += 5;
      });

      // Category match
      if (filters.category && product.category_id === filters.category) {
        score += 20;
      }

      // Brand match
      if (filters.brand && product.brand?.toLowerCase() === filters.brand?.toLowerCase()) {
        score += 15;
      }

      // Price preference
      if (filters.price_max && product.price <= filters.price_max) {
        score += 5;
      }

      // Rating boost
      if (product.rating || product.rating_avg) {
        const rating = product.rating || product.rating_avg;
        score += rating * 2;
      }

      // Popularity boost
      if (product.popularity_score) {
        score += product.popularity_score * 0.1;
      }

      return {
        ...product,
        match_score: Math.round(score * 10) / 10
      };
    })
    .sort((a, b) => b.match_score - a.match_score);
  }

  /**
   * Get product by ID
   */
  async getById(productId) {
    try {
      logger.info(`[ProductService] Getting product: ${productId}`);
      
      const sql = `
        SELECT * FROM products WHERE id = $1 AND is_active = true
      `;
      
      const result = await pool.query(sql, [productId]);
      
      if (result.rows.length === 0) {
        return null;
      }
      
      const row = result.rows[0];
      return {
        id: row.id,
        title: row.name,
        name: row.name,
        price: parseFloat(row.price),
        original_price: parseFloat(row.original_price),
        discount_percent: row.discount_percent,
        images: row.images,
        rating_avg: row.rating_avg,
        rating_count: row.rating_count,
        description: row.description,
        category_id: row.category_id,
        brand: row.brand
      };
    } catch (error) {
      logger.error('[ProductService] Error getting product:', error);
      throw error;
    }
  }

  /**
   * Get products by category IDs
   */
  async getByCategories(categoryIds, limit = 12, offset = 0, sort = '-popularity_score') {
    try {
      logger.info(`[ProductService] Getting products for categories:`, categoryIds);
      
      if (!categoryIds || categoryIds.length === 0) {
        return [];
      }

      // Parse sort parameter
      const sortField = sort.replace('-', '');
      const sortDir = sort.startsWith('-') ? 'DESC' : 'ASC';

      const sql = `
        SELECT id, name, slug, category_id, brand, price, original_price, 
               discount_percent, images, rating_avg, rating_count, popularity_score
        FROM products 
        WHERE category_id = ANY($1) AND is_active = true
        ORDER BY ${sortField} ${sortDir}
        LIMIT $2 OFFSET $3
      `;

      const result = await pool.query(sql, [categoryIds, limit, offset]);

      return result.rows.map(row => ({
        id: row.id,
        title: row.name,
        name: row.name,
        price: parseFloat(row.price),
        original_price: parseFloat(row.original_price),
        discount_percent: row.discount_percent,
        images: row.images,
        rating_avg: row.rating_avg,
        rating_count: row.rating_count
      }));
    } catch (error) {
      logger.error('[ProductService] Error getting products by categories:', error);
      return [];
    }
  }

  /**
   * Get similar products
   */
  async getSimilarProducts(productId, limit = 5) {
    try {
      logger.info(`[ProductService] Getting similar products for: ${productId}`);
      
      const product = await this.getById(productId);
      if (!product) return [];

      // Search by same category and similar price range
      const sql = `
        SELECT id, name, slug, category_id, brand, price, original_price, 
               discount_percent, images, rating_avg, rating_count
        FROM products 
        WHERE category_id = $1 
          AND id != $2
          AND price BETWEEN $3 AND $4
          AND is_active = true
        LIMIT $5
      `;

      const result = await pool.query(sql, [
        product.category_id,
        productId,
        product.price * 0.7,
        product.price * 1.3,
        limit
      ]);

      return result.rows.map(row => ({
        id: row.id,
        title: row.name,
        price: parseFloat(row.price),
        original_price: parseFloat(row.original_price),
        images: row.images,
        rating_avg: row.rating_avg
      }));
    } catch (error) {
      logger.error('[ProductService] Error getting similar products:', error);
      return [];
    }
  }
}

export const productService = new ProductService();
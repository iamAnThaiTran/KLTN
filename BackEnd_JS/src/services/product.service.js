import { logger } from '../utils/logger.js';

/**
 * Product Service
 * Xử lý search và filter products từ database
 * Layer này KHÔNG dùng LLM, chỉ query DB thuần túy
 */
class ProductService {
  constructor() {
    // TODO: Initialize database connection
    // this.db = database connection
  }

  /**
   * Search products từ database
   * @param {string} searchQuery - Search query đã được extract từ intent
   * @param {object} filters - Structured filters (price, category, brand...)
   * @returns {Promise<Array>} - Danh sách products
   */
  async searchProducts(searchQuery, filters = {}) {
    try {
      logger.info(`[ProductService] Searching: "${searchQuery}"`);
      logger.info(`[ProductService] Filters:`, filters);

      // === BUILD DATABASE QUERY ===
      const query = this.buildDatabaseQuery(searchQuery, filters);
      
      // === EXECUTE SEARCH ===
      // TODO: Implement actual database search
      // const results = await this.db.search(query);
      
      // TODO: Remove this mock data - implement real database query above
      const results = [];
      
      // === RANK RESULTS ===
      const rankedProducts = this.rankProducts(results, searchQuery, filters);
      
      logger.info(`[ProductService] Found ${rankedProducts.length} products`);
      
      return rankedProducts;

    } catch (error) {
      logger.error('[ProductService] Search error:', error);
      throw error;
    }
  }

  /**
   * Build database query từ search query và filters
   */
  buildDatabaseQuery(searchQuery, filters) {
    const query = {
      text_search: searchQuery,
      filters: {}
    };

    // Price range filter
    if (filters.price_min !== undefined || filters.price_max !== undefined) {
      query.filters.price = {};
      if (filters.price_min) query.filters.price.$gte = filters.price_min;
      if (filters.price_max) query.filters.price.$lte = filters.price_max;
    }

    // Category filter
    if (filters.category) {
      query.filters.category = filters.category;
    }

    // Brand filter
    if (filters.brand) {
      query.filters.brand = filters.brand;
    }

    // Usage filter (có thể map với tags hoặc specs)
    if (filters.usage) {
      query.filters.tags = { $contains: filters.usage };
    }

    return query;
  }

  /**
   * Rank products dựa trên relevance
   * Simple scoring algorithm
   */
  rankProducts(products, searchQuery, filters) {
    return products.map(product => {
      let score = 0;

      // Text relevance score
      const queryTerms = searchQuery.toLowerCase().split(' ');
      const titleLower = product.title.toLowerCase();
      const descLower = (product.description || '').toLowerCase();

      queryTerms.forEach(term => {
        if (titleLower.includes(term)) score += 10;
        if (descLower.includes(term)) score += 5;
      });

      // Category match
      if (filters.category && product.category === filters.category) {
        score += 20;
      }

      // Brand match
      if (filters.brand && product.brand === filters.brand) {
        score += 15;
      }

      // Price preference (products closer to max price get higher score)
      if (filters.price_max) {
        const priceRatio = product.price / filters.price_max;
        if (priceRatio <= 1) {
          score += (1 - priceRatio) * 10; // Cheaper = better
        }
      }

      // Rating boost
      if (product.rating) {
        score += product.rating * 2;
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
  async getProductById(productId) {
    try {
      logger.info(`[ProductService] Getting product: ${productId}`);
      
      // TODO: Implement real database query
      // return await this.db.findOne({ id: productId });
      
      return null; // No mock data - needs real database implementation
    } catch (error) {
      logger.error('[ProductService] Error getting product:', error);
      throw error;
    }
  }

  /**
   * Get similar products
   */
  async getSimilarProducts(productId, limit = 5) {
    try {
      logger.info(`[ProductService] Getting similar products for: ${productId}`);
      
      const product = await this.getProductById(productId);
      if (!product) return [];

      // Search by same category and similar price range
      return await this.searchProducts(product.category, {
        category: product.category,
        price_min: product.price * 0.7,
        price_max: product.price * 1.3
      });

    } catch (error) {
      logger.error('[ProductService] Error getting similar products:', error);
      return [];
    }
  }
}

export const productService = new ProductService();
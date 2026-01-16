import { productService } from '../services/product.service.js';
import { intentService } from '../services/intent.service.js';
import { llmService } from '../services/llm.service.js';
import { successResponse } from '../utils/response.js';
import { logger } from '../utils/logger.js';
import {pool} from '../config/database.js';

export async function search(req, res, next) {
  try {
    const { q, message, force_refresh, skip_clarify } = req.query;
    const userId = req.user?.id;
    
    logger.info(`[ProductController] Search request: "${q}", skip_clarify: ${skip_clarify}`);
    
    // Step 1: Analyze intent using SLM (unless skip_clarify is true)
    let intentAnalysis;
    if (skip_clarify === 'true') {
      logger.info('[ProductController] Skipping intent analysis');
      intentAnalysis = {
        intent_status: 'clear',
        extracted_constraints: {},
        intent_summary: q
      };
    } else {
      try {
        intentAnalysis = await intentService.analyzeIntent(q, [], {});
        logger.info('[ProductController] Intent analysis:', intentAnalysis);
      } catch (error) {
        logger.error('[ProductController] Intent analysis failed:', error);
        // Continue with basic search if intent analysis fails
        intentAnalysis = {
          intent_status: 'clear',
          extracted_constraints: {},
          intent_summary: q
        };
      }
    }

    // Step 2: Check if intent is clear enough to search
    if (intentAnalysis.intent_status === 'unclear' && skip_clarify !== 'true') {
      // Ask for clarification using overlay format
      const followUpQuestions = intentAnalysis.follow_up_questions || [];
      const firstQuestion = followUpQuestions[0];
      
      // Handle both string array and object array formats
      let options = [];
      if (firstQuestion) {
        if (typeof firstQuestion === 'string') {
          // If it's a string, use it directly
          options = [{ key: firstQuestion, label: firstQuestion }];
        } else if (firstQuestion.options && Array.isArray(firstQuestion.options)) {
          // If it's an object with options array
          options = firstQuestion.options.map(opt => ({
            key: typeof opt === 'string' ? opt : opt.key || opt,
            label: typeof opt === 'string' ? opt : opt.label || opt
          }));
        }
      }
      
      return successResponse(res, {
        ui_mode: 'OVERLAY_ASSIST',
        intent_summary: intentAnalysis.intent_summary || `✔ Đã hiểu: ${q}`,
        question: firstQuestion?.question || firstQuestion || 'Bạn có thể cung cấp thêm thông tin?',
        options: options,
        allow_skip: true,
        follow_up_questions: followUpQuestions
      }, 'Clarification needed');
    }

    // Step 3: Search products with extracted constraints
    const result = await productService.searchProducts(q, {
      ...intentAnalysis.extracted_constraints,
      message,
      forceRefresh: force_refresh === 'true',
      userId
    });

    // Step 4: Enhance results with LLM if products found
    let enhancedResults = result;
    if (result && result.length > 0) {
      try {
        // Generate explanations for top results
        enhancedResults = await Promise.all(
          result.slice(0, 5).map(async (product) => {
            try {
              const reason = await llmService.generateRecommendationReason(
                product,
                q,
                intentAnalysis.extracted_constraints
              );
              return {
                ...product,
                recommendationReason: reason
              };
            } catch (error) {
              logger.warn(`[ProductController] Failed to generate reason for ${product.id}:`, error);
              return product; // Return product without reason if enhancement fails
            }
          })
        );
      } catch (error) {
        logger.warn('[ProductController] LLM enhancement failed:', error);
        // Continue with original results if enhancement fails
      }
    }

    return successResponse(res, {
      type: 'query',
      products: enhancedResults,
      intentAnalysis: {
        status: intentAnalysis.intent_status,
        summary: intentAnalysis.intent_summary,
        constraints: intentAnalysis.extracted_constraints
      }
    }, 'Products fetched successfully');

  } catch (error) {
    logger.error('Product search error:', error);
    next(error);
  }
}

export async function getById(req, res, next) {
  try {
    const { id } = req.params;
    const product = await productService.getById(id);
    
    return successResponse(res, product);
  } catch (error) {
    next(error);
  }
}

export async function compareProducts(req, res, next) {
  try {
    const { productIds } = req.body;
    // Mock comparison for now
    const comparison = {
      products: [],
      comparison_matrix: {}
    };
    
    return successResponse(res, comparison, 'Products compared successfully');
  } catch (error) {
    logger.error('Product comparison error:', error);
    next(error);
  }
}

/**
 * Get products by category IDs
 * Query params: category_ids={id1},{id2}..., limit=12, sort=-popularity_score
 */
export async function getByCategories(req, res, next) {
  try {
    const { category_ids, limit = 12, offset = 0, sort = '-popularity_score' } = req.query;

    if (!category_ids) {
      return successResponse(res, [], 'No category IDs provided');
    }

    // Parse category IDs
    const categoryArray = category_ids.split(',').map(id => parseInt(id)).filter(id => !isNaN(id));

    if (categoryArray.length === 0) {
      return successResponse(res, [], 'Invalid category IDs');
    }

    // Build query
    let query = `
      SELECT id, name, slug, category_id, brand, description, price, original_price, 
             discount_percent, stock, images, rating_avg, rating_count, popularity_score, is_active, link, platform
      FROM products 
      WHERE category_id = ANY($1) AND is_active = true
    `;

    const params = [categoryArray];

    // Handle sorting
    if (sort === '-popularity_score') {
      query += ' ORDER BY popularity_score DESC';
    } else if (sort === 'price') {
      query += ' ORDER BY price ASC';
    } else if (sort === '-price') {
      query += ' ORDER BY price DESC';
    } else if (sort === '-rating_avg') {
      query += ' ORDER BY rating_avg DESC';
    } else {
      query += ' ORDER BY popularity_score DESC'; // Default
    }

    // Add limit and offset
    query += ` LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    params.push(parseInt(limit));
    params.push(parseInt(offset));

    logger.info(`[ProductController] Fetching products by categories`, { categoryArray, limit, offset, sort });

    const result = await pool.query(query, params);

    return successResponse(res, result.rows, 'Products fetched successfully');
  } catch (error) {
    logger.error('[ProductController] Error fetching products by categories:', error);
    next(error);
  }
}

/**
 * Get products by search term/category name
 * Query params: q={search}, limit=12, sort=-popularity_score
 */
export async function getBySearchTerm(req, res, next) {
  try {
    const { q, limit = 12, offset = 0, sort = '-popularity_score' } = req.query;

    if (!q) {
      return successResponse(res, [], 'No search term provided');
    }

    // Parse sort parameter
    const sortField = sort.replace('-', '');
    const sortDir = sort.startsWith('-') ? 'DESC' : 'ASC';

    const query = `
      SELECT id, name, slug, category_id, brand, description, price, original_price, 
             discount_percent, stock, images, rating_avg, rating_count, popularity_score, link, platform
      FROM products 
      WHERE is_active = true
      AND (
        name ILIKE $1 
        OR description ILIKE $1 
        OR brand ILIKE $1
      )
      ORDER BY ${sortField} ${sortDir}
      LIMIT $2 OFFSET $3
    `;

    logger.info(`[ProductController] Fetching products by search term: "${q}"`);

    const result = await pool.query(query, [`%${q}%`, limit, offset]);

    const products = result.rows.map(row => ({
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
      rating_avg: row.rating_avg,
      rating_count: row.rating_count,
      popularity_score: row.popularity_score,
      link: row.link,
      platform: row.platform
    }));

    return successResponse(res, products, 'Products fetched successfully');
  } catch (error) {
    logger.error('[ProductController] Error fetching products by search term:', error);
    next(error);
  }
}

// Export as 'compare' for router
export { compareProducts as compare };
import { productService } from '../services/product.service.js';
import { intentService } from '../services/intent.service.js';
import { llmService } from '../services/llm.service.js';
import { successResponse } from '../utils/response.js';
import { logger } from '../utils/logger.js';

export async function search(req, res, next) {
  try {
    const { q, message, force_refresh } = req.query;
    const userId = req.user?.id;
    
    logger.info(`[ProductController] Search request: "${q}"`);
    
    // Step 1: Analyze intent using SLM
    let intentAnalysis;
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

    // Step 2: Check if intent is clear enough to search
    if (intentAnalysis.intent_status === 'unclear') {
      // Ask for clarification using overlay format
      return successResponse(res, {
        ui_mode: 'OVERLAY_ASSIST',
        summary: `✔ Đã hiểu: ${q}`,
        question: intentAnalysis.follow_up_questions?.[0] || 'Bạn có thể cung cấp thêm thông tin?',
        options: (intentAnalysis.follow_up_questions || []).map((q, index) => ({
          key: `option_${index}`,
          label: q
        })),
        allow_skip: true
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

// Export as 'compare' for router
export { compareProducts as compare };
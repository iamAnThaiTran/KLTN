import { productService } from '../services/product.service.js';
import { successResponse, errorResponse } from '../utils/response.js';
import { logger } from '../utils/logger.js';

export async function search(req, res, next) {
  try {
    const { q, message, force_refresh } = req.query;
    const userId = req.user?.id;
    
    const result = await productService.search({
      query: q,
      message,
      forceRefresh: force_refresh === 'true',
      userId
    });
    
    return successResponse(res, result, 'Products fetched successfully');
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
    const comparison = await productService.compare(productIds);
    
    return successResponse(res, comparison);
  } catch (error) {
    next(error);
  }
}s
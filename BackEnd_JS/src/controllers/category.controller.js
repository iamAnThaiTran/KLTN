import { logger } from '../utils/logger.js';
import { successResponse, errorResponse } from '../utils/response.js';
import {pool} from '../config/database.js';

/**
 * Get categories with filtering options and associated products
 * Query params: level=0|1|2, parent_id={id}, limit=10, offset=0, include_products=true
 */
export async function getCategories(req, res, next) {
  try {
    const { level, parent_id, limit = 20, offset = 0, include_products = 'true' } = req.query;

    let query = 'SELECT * FROM categories WHERE is_active = true';
    const params = [];

    // Filter by level if provided
    if (level !== undefined) {
      query += ` AND level = $${params.length + 1}`;
      params.push(parseInt(level));
    }

    // Filter by parent_id if provided
    if (parent_id !== undefined) {
      query += ` AND parent_id = $${params.length + 1}`;
      params.push(parseInt(parent_id));
    }

    // Add ordering and pagination
    query += ` ORDER BY priority DESC, name ASC`;
    query += ` LIMIT $${params.length + 1} OFFSET $${params.length + 2}`;
    params.push(parseInt(limit));
    params.push(parseInt(offset));

    logger.info(`[CategoryController] Fetching categories`, { level, parent_id, limit, offset });

    const result = await pool.query(query, params);

    // If include_products is true, fetch products for each category
    const shouldIncludeProducts = include_products === 'true';
    
    if (shouldIncludeProducts && result.rows.length > 0) {
      const categoriesWithProducts = await Promise.all(
        result.rows.map(async (category) => {
          try {
            // Get products directly by category_id and subcategories
            const productsResult = await pool.query(`
              SELECT id, name, slug, category_id, brand, description, price, original_price, 
                     discount_percent, stock, images, rating_avg, rating_count, popularity_score, link, platform
              FROM products 
              WHERE is_active = true
              AND (
                category_id = $1
                OR category_id IN (
                  SELECT id FROM categories WHERE parent_id = $1
                )
              )
              ORDER BY popularity_score DESC, rating_avg DESC
              LIMIT 12
            `, [category.id]);

            const products = productsResult.rows.map(row => ({
              id: row.id,
              title: row.name,
              name: row.name,
              slug: row.slug,
              brand: row.brand,
              price: parseFloat(row.price),
              original_price: parseFloat(row.original_price),
              discount_percent: row.discount_percent,
              images: row.images,
              rating_avg: row.rating_avg,
              rating_count: row.rating_count,
              popularity_score: row.popularity_score,
              link: row.link,
              platform: row.platform
            }));

            return {
              ...category,
              products,
              product_count: products.length
            };
          } catch (err) {
            logger.warn(`[CategoryController] Failed to fetch products for category ${category.id}:`, err.message);
            return {
              ...category,
              products: [],
              product_count: 0
            };
          }
        })
      );

      return successResponse(res, categoriesWithProducts, 'Categories with products fetched successfully');
    }

    return successResponse(res, result.rows, 'Categories fetched successfully');
  } catch (error) {
    logger.error('[CategoryController] Error fetching categories:', error);
    next(error);
  }
}

/**
 * Get category by ID with products and subcategories
 */
export async function getCategoryById(req, res, next) {
  try {
    const { id } = req.params;
    const { limit = 12, offset = 0 } = req.query;

    logger.info(`[CategoryController] Getting category ${id} with products`);

    // Get category
    const categoryResult = await pool.query(
      'SELECT * FROM categories WHERE id = $1 AND is_active = true',
      [id]
    );

    if (categoryResult.rows.length === 0) {
      return errorResponse(res, 'Category not found', 404);
    }

    const category = categoryResult.rows[0];

    // Get subcategories
    const subResult = await pool.query(
      'SELECT * FROM categories WHERE parent_id = $1 AND is_active = true ORDER BY priority DESC, name ASC',
      [id]
    );

    const subcategories = subResult.rows;

    // Get products for this category and its subcategories
    let productsQuery = `
      SELECT id, name, slug, category_id, brand, description, price, original_price, 
             discount_percent, stock, images, rating_avg, rating_count, popularity_score, link, platform
      FROM products 
      WHERE is_active = true
      AND (
        category_id = $1
        OR category_id IN (
          SELECT id FROM categories WHERE parent_id = $1
        )
      )
      ORDER BY popularity_score DESC, rating_avg DESC
      LIMIT $2 OFFSET $3
    `;

    const productsResult = await pool.query(productsQuery, [id, limit, offset]);

    const products = productsResult.rows.map(row => ({
      id: row.id,
      title: row.name,
      name: row.name,
      slug: row.slug,
      brand: row.brand,
      price: parseFloat(row.price),
      original_price: parseFloat(row.original_price),
      discount_percent: row.discount_percent,
      images: row.images,
      rating_avg: row.rating_avg,
      rating_count: row.rating_count,
      popularity_score: row.popularity_score,
      link: row.link,
      platform: row.platform
    }));

    return successResponse(res, {
      category,
      subcategories,
      products,
      productsCount: products.length
    }, 'Category with products fetched successfully');
  } catch (error) {
    logger.error('[CategoryController] Error getting category:', error);
    next(error);
  }
}

//     const categoryQuery = 'SELECT * FROM categories WHERE id = $1';
//     const categoryResult = await pool.query(categoryQuery, [id]);

//     if (categoryResult.rows.length === 0) {
//       return errorResponse(res, 'Category not found', 404);
//     }

//     const category = categoryResult.rows[0];

//     // Get subcategories if this is a main category (level 0)
//     let subcategories = [];
//     if (category.level === 0) {
//       const subQuery = `
//         SELECT * FROM categories 
//         WHERE parent_id = $1 AND is_active = true 
//         ORDER BY priority DESC, name ASC
//       `;
//       const subResult = await pool.query(subQuery, [id]);
//       subcategories = subResult.rows;
//     }

//     return successResponse(res, {
//       ...category,
//       subcategories
//     }, 'Category fetched successfully');
//   } catch (error) {
//     logger.error('[CategoryController] Error fetching category:', error);
//     next(error);
//   }
// }

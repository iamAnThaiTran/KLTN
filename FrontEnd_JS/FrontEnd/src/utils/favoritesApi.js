/**
 * Favorites API Utilities
 * Handles all favorite-related API calls
 */

import apiRequest from './apiClient.js';

/**
 * Get all favorites for the user
 * @param {string} userId - User ID from auth context
 * @param {number} limit - Number of results
 * @param {number} offset - Pagination offset
 * @returns {Promise<Object>} Favorites list with product details
 */
export async function getUserFavorites(userId, { limit = 50, offset = 0 } = {}) {
  try {
    if (!userId) throw new Error('User ID is required');
    
    const response = await apiRequest(`/api/users/${userId}/favorites?limit=${limit}&offset=${offset}`, {
      method: 'GET'
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized - please login again');
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Favorites API] Error getting favorites:', error);
    throw error;
  }
}

/**
 * Add a product to favorites
 * @param {string} userId - User ID from auth context
 * @param {number} productId - Product ID
 * @param {number} skuId - Optional SKU ID
 * @param {number} price - Optional current price
 * @returns {Promise<Object>} Response with favorite info
 */
export async function addToFavorites(userId, productId, skuId = null, price = null) {
  try {
    if (!userId) throw new Error('User ID is required');
    if (productId === undefined || productId === null) throw new Error('Product ID is required');
    
    const response = await apiRequest(`/api/users/${userId}/favorites`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        product_id: productId,
        sku_id: skuId,
        price: price
      })
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized - please login again');
      if (response.status === 404) throw new Error('Product not found');
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Favorites API] Error adding to favorites:', error);
    throw error;
  }
}

/**
 * Remove a product from favorites
 * @param {string} userId - User ID from auth context
 * @param {number} productId - Product ID
 * @returns {Promise<Object>} Response with success status
 */
export async function removeFromFavorites(userId, productId) {
  try {
    if (!userId) throw new Error('User ID is required');
    if (!productId) throw new Error('Product ID is required');
    
    const response = await apiRequest(`/api/users/${userId}/favorites/${productId}`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized - please login again');
      if (response.status === 404) throw new Error('Favorite not found');
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Favorites API] Error removing from favorites:', error);
    throw error;
  }
}

/**
 * Check if a product is in user's favorites
 * @param {string} userId - User ID from auth context
 * @param {number} productId - Product ID
 * @returns {Promise<boolean>} True if favorited, false otherwise
 */
export async function checkFavoriteStatus(userId, productId) {
  try {
    if (!userId) throw new Error('User ID is required');
    if (!productId) throw new Error('Product ID is required');
    
    const response = await apiRequest(`/api/users/${userId}/favorites/${productId}`, {
      method: 'GET'
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized - please login again');
      throw new Error(`HTTP ${response.status}`);
    }

    const data = await response.json();
    return data.is_favorite;
  } catch (error) {
    console.error('[Favorites API] Error checking favorite status:', error);
    throw error;
  }
}

/**
 * Clear all favorites for the user
 * @param {string} userId - User ID from auth context
 * @returns {Promise<Object>} Response with deleted count
 */
export async function clearAllFavorites(userId) {
  try {
    if (!userId) throw new Error('User ID is required');
    
    const response = await apiRequest(`/api/users/${userId}/favorites`, {
      method: 'DELETE'
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized - please login again');
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Favorites API] Error clearing favorites:', error);
    throw error;
  }
}

/**
 * Compare multiple products
 * @param {number[]} productIds - Array of product IDs to compare
 * @returns {Promise<Object>} Comparison result
 */
export async function compareProducts(productIds) {
  try {
    if (!Array.isArray(productIds) || productIds.length < 2) {
      throw new Error('At least 2 products required for comparison');
    }

    const response = await apiRequest(`/api/products/compare`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        product_ids: productIds,
      }),
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized - please login again');
      if (response.status === 400) throw new Error('Invalid product IDs');
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Favorites API] Error comparing products:', error);
    throw error;
  }
}

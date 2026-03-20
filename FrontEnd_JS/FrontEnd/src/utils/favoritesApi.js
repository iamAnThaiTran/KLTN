/**
 * Favorites API Utilities
 * Handles all favorite-related API calls
 */

import apiRequest from './apiClient.js';

/**
 * Get all favorites for the user
 * @param {number} limit - Number of results
 * @param {number} offset - Pagination offset
 * @returns {Promise<Object>} Favorites list with product details
 */
export async function getUserFavorites({ limit = 50, offset = 0 } = {}) {
  try {
    const response = await apiRequest(`/api/user/favorites?limit=${limit}&offset=${offset}`, {
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
 * @param {number} productId - Product ID
 * @returns {Promise<Object>} Response with favorite info
 */
export async function addToFavorites(productId) {
  try {
    const response = await apiRequest(`/api/user/favorites/${productId}`, {
      method: 'POST'
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
 * @param {number} productId - Product ID
 * @returns {Promise<Object>} Response with success status
 */
export async function removeFromFavorites(productId) {
  try {
    const response = await apiRequest(`/api/user/favorites/${productId}`, {
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
 * @param {number} productId - Product ID
 * @returns {Promise<boolean>} True if favorited, false otherwise
 */
export async function checkFavoriteStatus(productId) {
  try {
    const response = await apiRequest(`/api/user/favorites/${productId}/status`, {
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
 * @returns {Promise<Object>} Response with deleted count
 */
export async function clearAllFavorites() {
  try {
    const response = await apiRequest(`/api/user/favorites`, {
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

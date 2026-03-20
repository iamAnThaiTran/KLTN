/**
 * Favorites API Utilities
 * Handles all favorite-related API calls
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Get all favorites for the user
 * @param {string} token - JWT token
 * @param {number} limit - Number of results
 * @param {number} offset - Pagination offset
 * @returns {Promise<Object>} Favorites list with product details
 */
export async function getUserFavorites(token, { limit = 50, offset = 0 } = {}) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/user/favorites?limit=${limit}&offset=${offset}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
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
 * @param {string} token - JWT token
 * @returns {Promise<Object>} Response with favorite info
 */
export async function addToFavorites(productId, token) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/user/favorites/${productId}`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
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
 * @param {string} token - JWT token
 * @returns {Promise<Object>} Response with success status
 */
export async function removeFromFavorites(productId, token) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/user/favorites/${productId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
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
 * @param {string} token - JWT token
 * @returns {Promise<boolean>} True if favorited, false otherwise
 */
export async function checkFavoriteStatus(productId, token) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/user/favorites/${productId}/status`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
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
 * @param {string} token - JWT token
 * @returns {Promise<Object>} Response with deleted count
 */
export async function clearAllFavorites(token) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/user/favorites`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!response.ok) {
      if (response.status === 401) throw new Error('Unauthorized');
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('[Favorites API] Error clearing favorites:', error);
    throw error;
  }
}

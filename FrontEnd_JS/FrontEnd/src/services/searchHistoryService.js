/**
 * Search History Service
 * Handles fetching user's search history and recommendations from backend
 */

const API_BASE = 'http://localhost:8000';

export class SearchHistoryService {
  /**
   * Get user's search history (actual search queries)
   * Source: Backend GET /api/user/search-history
   */
  static async getSearchHistory(token, limit = 20, days = 30) {
    try {
      const response = await fetch(
        `${API_BASE}/api/user/search-history?limit=${limit}&days=${days}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[SearchHistoryService] Error fetching search history:', error);
      throw error;
    }
  }

  /**
   * Get user's search preferences and interests
   * Source: Backend GET /api/recommendations/preferences
   */
  static async getUserPreferences(token) {
    try {
      const response = await fetch(`${API_BASE}/api/recommendations/preferences`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[SearchHistoryService] Error fetching preferences:', error);
      throw error;
    }
  }

  /**
   * Get recommended products for homepage
   * Source: Backend GET /api/recommendations/homepage
   */
  static async getRecommendedProducts(token) {
    try {
      const response = await fetch(`${API_BASE}/api/recommendations/homepage`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[SearchHistoryService] Error fetching recommendations:', error);
      throw error;
    }
  }
}

export default SearchHistoryService;
